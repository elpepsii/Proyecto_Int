"""
carrito_views.py — Vistas del circuito de compra (RF-05, RF-06, RF-18, RF-20).

El circuito completo del e-commerce:
  1) agregar / ver / actualizar / quitar  -> carrito en la sesión
  2) checkout                             -> crea la Venta PENDIENTE usando
     venta.agregar_producto() (la regla de negocio sigue en models.py) y
     redirige al pago WebPay
  3) mis_pedidos                          -> el cliente ve sus ventas y puede
     (re)intentar el pago de las que quedaron PENDIENTES

Reparto de responsabilidades (igual que conversamos):
  - Estas vistas SOLO orquestan: leen el carrito, llaman al modelo, redirigen.
  - Totales y subtotales los calcula models.py (DetalleVenta.save(),
    Venta.recalcular_total()). Ninguna vista escribe 'total' a mano.
  - El stock se CONSULTA para avisar al cliente, no se descuenta aquí:
    el descuento real corresponde al momento en que el pago se AUTORIZA
    (sprint de stock, ver README).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import carrito as carrito_ayuda
from .models import EstadoVenta, OrigenVenta, Producto, Stock, Venta


# ----------------------------------------------------------------- helpers
def _leer_cantidad(request, defecto=1):
    """Convierte el input 'cantidad' del POST a int sin romperse si viene
    vacío o con basura. Nunca devuelve menos de 1."""
    try:
        return max(1, int(request.POST.get('cantidad', defecto)))
    except (TypeError, ValueError):
        return defecto


def _stock_disponible(producto):
    """Total sala + bodega (0 si el producto aún no tiene fila de Stock)."""
    stock = Stock.objects.filter(producto=producto).first()
    return stock.stock_total if stock else 0


# ----------------------------------------------------------------- carrito
@require_POST
def agregar_al_carrito(request, producto_id):
    """RF-05: agrega N unidades al carrito respetando el stock disponible.
    Es POST porque MODIFICA estado (nunca un GET: evita que un bot/link
    o un prefetch del navegador agregue productos sin querer)."""
    producto = get_object_or_404(Producto, pk=producto_id, activo=True)
    cantidad = _leer_cantidad(request)
    disponible = _stock_disponible(producto)

    el_carrito = carrito_ayuda.obtener_carrito(request)
    clave = str(producto.pk)
    ya_tiene = int(el_carrito.get(clave, 0))

    # Se ajusta a lo que realmente hay (jamás se promete más stock).
    nueva_cantidad = min(ya_tiene + cantidad, disponible)
    if nueva_cantidad <= 0:
        messages.error(request,
                       f'"{producto.nombre}" no tiene stock disponible.')
    elif nueva_cantidad < ya_tiene + cantidad:
        el_carrito[clave] = nueva_cantidad
        carrito_ayuda.guardar_carrito(request, el_carrito)
        messages.warning(request,
                         f'Solo hay {disponible} unidades de '
                         f'"{producto.nombre}". Se ajustó la cantidad.')
    else:
        el_carrito[clave] = nueva_cantidad
        carrito_ayuda.guardar_carrito(request, el_carrito)
        messages.success(request,
                         f'Agregado al carrito: {producto.nombre} × {cantidad}.')

    return redirect('tiendaApp:ver_carrito')


@require_POST
def actualizar_linea(request, producto_id):
    """Cambia la cantidad de una línea desde el input del carrito."""
    el_carrito = carrito_ayuda.obtener_carrito(request)
    clave = str(producto_id)
    if clave not in el_carrito:
        return redirect('tiendaApp:ver_carrito')

    producto = get_object_or_404(Producto, pk=producto_id)
    disponible = _stock_disponible(producto)
    cantidad = min(_leer_cantidad(request), disponible)

    if cantidad <= 0:
        del el_carrito[clave]
        carrito_ayuda.guardar_carrito(request, el_carrito)
        messages.warning(request, f'Sin stock de "{producto.nombre}": '
                                  f'el producto se quitó del carrito.')
    else:
        el_carrito[clave] = cantidad
        carrito_ayuda.guardar_carrito(request, el_carrito)

    return redirect('tiendaApp:ver_carrito')


@require_POST
def quitar_linea(request, producto_id):
    el_carrito = carrito_ayuda.obtener_carrito(request)
    if str(producto_id) in el_carrito:
        del el_carrito[str(producto_id)]
        carrito_ayuda.guardar_carrito(request, el_carrito)
        messages.info(request, 'Producto quitado del carrito.')
    return redirect('tiendaApp:ver_carrito')


def ver_carrito(request):
    """RF-05: muestra el carrito con el desglose IVA (los precios en Chile
    ya lo incluyen: neto = total / 1.19, igual que Venta.monto_neto)."""
    el_carrito = carrito_ayuda.obtener_carrito(request)
    lineas, total = carrito_ayuda.resumen_carrito(el_carrito)
    neto = round(total / 1.19)
    return render(request, 'tiendaApp/carrito.html', {
        'lineas': lineas,
        'total': total,
        'neto': neto,
        'iva': total - neto,
    })


# ---------------------------------------------------------------- checkout
@login_required
@require_POST
def checkout(request):
    """RF-06 / RF-18: convierte el carrito en una Venta PENDIENTE y manda
    al cliente al paso WebPay.

    ¿Por qué POST? Crea registros: un GET podría dispararlo por accidente
    (un crawler, un prefetch del navegador, F5 duplicado...).
    ¿Por qué transaction.atomic? O se crea la venta CON TODOS sus detalles,
    o no se crea nada (evita ventas a medio armar si algo falla a la mitad).
    """
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente is None:
        # Un admin sin perfil de cliente no puede comprar por la web.
        messages.error(request,
                       'Tu usuario no tiene perfil de cliente (¿entraste '
                       'como administrador?). Regístrate como cliente para '
                       'comprar en la tienda.')
        return redirect('tiendaApp:home')

    lineas, _total = carrito_ayuda.resumen_carrito(
        carrito_ayuda.obtener_carrito(request))
    if not lineas:
        messages.warning(request, 'Tu carrito está vacío.')
        return redirect('tiendaApp:ver_carrito')

    with transaction.atomic():
        venta = Venta.objects.create(
            origen=OrigenVenta.WEB,
            cliente=cliente,
            estado=EstadoVenta.PENDIENTE,
        )
        for linea in lineas:
            # ÚNICA puerta de entrada al total: agregar_producto congela el
            # precio vigente (snapshot) y recalcula el total de la venta.
            venta.agregar_producto(linea['producto'], linea['cantidad'])

    carrito_ayuda.vaciar_carrito(request)
    messages.success(request,
                     f'Venta #{venta.id} creada. Sigue con el pago.')
    # El flujo continúa en la app webpay (paso 1: iniciar la transacción).
    return redirect('webpay:iniciar', venta_id=venta.id)


# --------------------------------------------------------------- pedidos
@login_required
def mis_pedidos(request):
    """RF-20 (parte web): listado de ventas del cliente logueado. Desde aquí
    puede pagar (o reintentar el pago de) las que quedaron PENDIENTES."""
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente is None:
        messages.error(request, 'Tu usuario no tiene perfil de cliente.')
        return redirect('tiendaApp:home')

    ventas = cliente.ventas.prefetch_related('detalles__producto')
    return render(request, 'tiendaApp/mis_pedidos.html', {'ventas': ventas})
