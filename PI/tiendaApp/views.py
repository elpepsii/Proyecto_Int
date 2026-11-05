"""
views.py — Vistas de la tienda PetShop.

Observa el reparto que conversamos (principio "fat model"):
  - Aquí va la ORQUESTACIÓN: qué se muestra, qué filtros se leen del GET,
    qué formularios se validan y a dónde se redirige.
  - Las REGLAS DE NEGOCIO viven en models.py: agregar_producto(),
    recalcular_total(), descontar_stock(), Pago.save() (máquina de estados),
    JornadaLaboral.abrir()/cerrar()/resumen_turno(). Ninguna vista escribe
    'total', 'subtotal' ni descuenta stock a mano.

Secciones:
  1. Tienda pública     (home, catálogo con filtros avanzados, detalle)
  2. Fichas de mascota  (mis fichas, crear, editar)          RF-08
  3. Cuenta             (registro solo clientes RF-07, perfil)
  4. Carrito            (ver, agregar, actualizar, quitar)   RF-05
  5. Checkout y compras (checkout, mis compras, detalle)     RF-06
  6. Vendedor           (panel, POS RF-18, ventas, entregas RF-20,
                         jornadas RF-24, crear vendedor RF-12)
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import carrito as carrito_ayuda
from .forms import (CheckoutForm, FichaForm, PerfilForm, POSVentaForm,
                    RegistroForm, VendedorForm)
from .models import (Cliente, Entrega, EstadoPago, EstadoVenta, Especie,
                     Ficha, JornadaLaboral, OrigenVenta, Pago, Producto,
                     Stock, TamanoGrano, Vendedor, Venta)


# =====================================================================
# 1. TIENDA PÚBLICA (RF-01, RF-02, RF-03, RF-04)
# =====================================================================
def home(request):
    """Portada: carrusel de banners + categorías + promociones + destacados.

    - categorias: tarjetas que llevan al catálogo ya filtrado (reutilizan
      los mismos filtros GET de lista_productos: especie y tipo).
    - promociones: productos a los que el admin les asignó 'precio_oferta'.
    - destacados: hasta 8 productos activos (igual que antes)."""
    promociones = (Producto.objects
                   .filter(activo=True, precio_oferta__isnull=False)
                   .select_related('stock')[:4])
    destacados = (Producto.objects
                  .filter(activo=True)
                  .select_related('stock')
                  .order_by('nombre')[:8])
    return render(request, 'tiendaApp/home.html',
                  {'destacados': destacados, 'promociones': promociones})


def lista_productos(request):
    """Catálogo con BÚSQUEDA AVANZADA por GET (RF-02 + RF-03):

      q            búsqueda por nombre o SKU
      especie      perro / gato / especial          (Producto.animal)
      tipo         alimento / higiene / juguete...  (Producto.tipo_producto)
      edad         cachorro / adulto / senior       (Producto.edad_producto)
      tamano_raza  pequeña / mediana / grande
      tamano_grano pequeño / mediano / grande      (solo alimentos)
      precio_min / precio_max   rango de precio en CLP
      orden        nombre (defecto) / precio_asc / precio_desc
      ficha        id de una ficha de mascota del cliente: filtra productos
                   COMPATIBLES con la mascota (misma especie, sin sus
                   alérgenos, tamaño de grano preferido). Es la razón de ser
                   de las fichas (RF-08): personalizar la búsqueda.

    Todo es acumulable y la paginación conserva los filtros elegidos.
    """
    productos = (Producto.objects
                 .filter(activo=True)
                 .select_related('stock'))

    q = request.GET.get('q', '').strip()
    especie = request.GET.get('especie', '')
    tipo = request.GET.get('tipo', '')
    edad = request.GET.get('edad', '')
    tamano_raza = request.GET.get('tamano_raza', '')
    tamano_grano = request.GET.get('tamano_grano', '')
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    orden = request.GET.get('orden', 'nombre')
    ficha_id = request.GET.get('ficha', '')

    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(sku__icontains=q))
    if especie:
        productos = productos.filter(animal=especie)
    if tipo:
        productos = productos.filter(tipo_producto=tipo)
    if edad:
        productos = productos.filter(edad_producto=edad)
    if tamano_raza:
        productos = productos.filter(tamano_raza=tamano_raza)
    if tamano_grano:
        productos = productos.filter(tamano_grano=tamano_grano)

    # Rango de precio: se convierte a int de forma segura; si viene basura,
    # simplemente se ignora el filtro (no revienta la página).
    # OJO: 'precio_min'/'precio_max' son nombres del GET, no campos del
    # modelo; el campo real es 'precio' (>= mínimo, <= máximo).
    if precio_min.isdigit():
        productos = productos.filter(precio__gte=int(precio_min))
    if precio_max.isdigit():
        productos = productos.filter(precio__lte=int(precio_max))

    # Filtro "compatible con mi mascota" (usa la ficha elegida)
    ficha = None
    if ficha_id:
        cliente = getattr(request.user, 'cliente_perfil', None)
        if cliente:
            ficha = cliente.fichas_mascotas.filter(pk=ficha_id).first()
        if ficha:
            productos = productos.filter(animal=ficha.especie)
            if ficha.tamano_grano_preferido:
                productos = productos.filter(
                    Q(tamano_grano=ficha.tamano_grano_preferido)
                    | Q(tamano_grano__isnull=True))
            alergenos = list(ficha.alergias.values_list('pk', flat=True))
            if alergenos:
                productos = (productos
                             .exclude(alergenos_contenidos__in=alergenos)
                             .distinct())

    ordenes = {
        'nombre': 'nombre',
        'precio_asc': 'precio',
        'precio_desc': '-precio',
    }
    productos = productos.order_by(ordenes.get(orden, 'nombre'))

    paginator = Paginator(productos, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Querystring sin 'page', para que los links de paginación conserven
    # los filtros que el usuario ya había elegido.
    filtros = request.GET.copy()
    filtros.pop('page', None)

    # Fichas del cliente para el select "comprar según mi mascota"
    fichas_cliente = []
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente:
        fichas_cliente = cliente.fichas_mascotas.prefetch_related('alergias')

    return render(request, 'tiendaApp/lista_productos.html', {
        'page_obj': page_obj,
        'q': q,
        'especie_actual': especie,
        'tipo_actual': tipo,
        'edad_actual': edad,
        'raza_actual': tamano_raza,
        'grano_actual': tamano_grano,
        'precio_min': precio_min,
        'precio_max': precio_max,
        'orden_actual': orden,
        'ficha_seleccionada': ficha,
        'fichas_cliente': fichas_cliente,
        'especies': Especie.choices,
        'tipos': Producto.TipoProducto.choices,
        'edades': Producto.EtapaVida.choices,
        'razas': Producto.TamanoRaza.choices,
        'granos': TamanoGrano.choices,
        'querystring': filtros.urlencode(),
    })


def detalle_producto(request, producto_id):
    """Ficha pública del producto: datos, alérgenos, stock y proveedores."""
    producto = get_object_or_404(Producto, pk=producto_id, activo=True)

    # .first() en vez de producto.stock: si algún producto aún no tiene
    # fila de Stock, no lanza excepción (solo muestra 'sin registro').
    stock = Stock.objects.filter(producto=producto).first()

    return render(request, 'tiendaApp/detalle_producto.html', {
        'producto': producto,
        'stock': stock,
    })


# =====================================================================
# 2. FICHAS DE MASCOTA (RF-08)
# =====================================================================
@login_required
def mis_fichas(request):
    """Listado de mascotas del cliente logueado.

    cliente_perfil es el related_name de Cliente.usuario_auth (OneToOne):
    desde el User se llega directo a su perfil de cliente.
    """
    cliente = getattr(request.user, 'cliente_perfil', None)
    fichas = cliente.fichas_mascotas.all() if cliente else []
    return render(request, 'tiendaApp/mis_fichas.html', {'fichas': fichas})


@login_required
def crear_ficha(request):
    """Crea una ficha nueva para el cliente logueado.

    favoritos y alergias son M2M: se guardan con save_m2m() DESPUÉS de
    persistir la ficha (Django exige que la fila exista para enlazar).
    """
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente is None:
        messages.error(request, 'Solo los clientes tienen fichas de mascota.')
        return redirect('tiendaApp:home')

    if request.method == 'POST':
        form = FichaForm(request.POST)
        if form.is_valid():
            # RNF-15: una cuenta puede tener un máximo de 20 fichas.
            if cliente.fichas_mascotas.count() >= 20:
                form.add_error(None, 'Tu cuenta ya tiene el máximo de '
                                     '20 fichas de mascota (RNF-15).')
            else:
                ficha = form.save(commit=False)
                ficha.cliente = cliente  # nunca del POST
                ficha.save()
                form.save_m2m()  # casillas de favoritos y alergias
                messages.success(request, f'Ficha de {ficha.nombre} creada.')
                return redirect('tiendaApp:mis_fichas')
    else:
        form = FichaForm()
    return render(request, 'tiendaApp/ficha_form.html', {'form': form})


@login_required
def editar_ficha(request, ficha_id):
    """Edita una ficha SOLO si pertenece al cliente logueado (protección
    de propiedad: el filtro por cliente va en la consulta, no a confiar)."""
    ficha = get_object_or_404(
        Ficha, pk=ficha_id, cliente__usuario_auth=request.user)

    if request.method == 'POST':
        form = FichaForm(request.POST, instance=ficha)
        if form.is_valid():
            form.save()  # con instance, save() también guarda los M2M
            messages.success(request, 'Ficha actualizada.')
            return redirect('tiendaApp:mis_fichas')
    else:
        form = FichaForm(instance=ficha)
    return render(request, 'tiendaApp/ficha_form.html',
                  {'form': form, 'ficha': ficha})


# =====================================================================
# 3. CUENTA (RF-07 registro de clientes; vendedores los crea el admin)
# =====================================================================
def registrar(request):
    """Registro SOLO para clientes: crea el User (auth) y su perfil Cliente.
    Los vendedores NO se registran aquí: los crea el administrador (RF-12)."""
    if request.user.is_authenticated:
        return redirect('tiendaApp:home')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            Cliente.objects.create(
                usuario_auth=user,
                apellido=form.cleaned_data['apellido'],
                correo=form.cleaned_data['email'],
                telefono=form.cleaned_data['telefono'] or None,
                direccion=form.cleaned_data['direccion'],
            )
            # queda logueado de inmediato. Con varios AUTHENTICATION_BACKENDS,
            # Django exige indicar cuál quedó asociado a la sesión (el
            # estándar: el usuario acaba de crearse con su contraseña).
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'¡Bienvenido/a, {user.get_full_name()}! '
                                      'Tu cuenta de cliente está lista.')
            return redirect('tiendaApp:home')
    else:
        form = RegistroForm()
    return render(request, 'registration/registro.html', {'form': form})

@login_required
def perfil(request):
    """Ver y editar los datos del cliente logueado."""
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente is None:
        messages.error(request, 'Tu usuario no tiene perfil de cliente.')
        return redirect('tiendaApp:home')

    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=cliente)
        if form.is_valid():
            cliente = form.save()
            # Sincroniza también el nombre/correo del User de Django
            request.user.first_name = form.cleaned_data['first_name']
            request.user.email = form.cleaned_data['email']
            request.user.save(update_fields=['first_name', 'email'])
            messages.success(request, 'Perfil actualizado.')
            return redirect('tiendaApp:perfil')
    else:
        form = PerfilForm(instance=cliente, initial={
            'first_name': request.user.first_name,
            'email': request.user.email,
        })
    return render(request, 'tiendaApp/perfil.html', {'form': form})


# =====================================================================
# 4. CARRITO (RF-05)
# =====================================================================
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
                                  'el producto se quitó del carrito.')
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


@require_POST
def vaciar_carrito(request):
    carrito_ayuda.vaciar_carrito(request)
    messages.info(request, 'Carrito vaciado.')
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


# =====================================================================
# 5. CHECKOUT Y COMPRAS (RF-06)
# =====================================================================
@login_required
def checkout(request):
    """Convierte el carrito en una Venta PENDIENTE (+ su Entrega) y manda
    al cliente al paso WebPay.

    GET  : muestra el formulario de entrega/documento y el resumen.
    POST : crea TODO dentro de transaction.atomic: o se crea la venta CON
           TODOS sus detalles, o no se crea nada.
    """
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente is None:
        messages.error(request,
                       'Tu usuario no tiene perfil de cliente (¿entraste '
                       'como vendedor o administrador?). Solo los clientes '
                       'compran por la web.')
        return redirect('tiendaApp:home')

    lineas, total = carrito_ayuda.resumen_carrito(
        carrito_ayuda.obtener_carrito(request))
    if not lineas:
        messages.warning(request, 'Tu carrito está vacío.')
        return redirect('tiendaApp:ver_carrito')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            with transaction.atomic():
                venta = Venta.objects.create(
                    origen=OrigenVenta.WEB,
                    cliente=cliente,
                    estado=EstadoVenta.PENDIENTE,
                    tipo_documento=datos['tipo_documento'],
                    rut_factura=datos.get('rut_factura'),
                    razon_social=datos.get('razon_social'),
                )
                for linea in lineas:
                    # ÚNICA puerta de entrada al total: agregar_producto
                    # congela el precio vigente (snapshot) y recalcula.
                    venta.agregar_producto(linea['producto'],
                                           linea['cantidad'])
                # Entrega (snapshot de la dirección al momento de comprar)
                Entrega.objects.create(
                    venta=venta,
                    tipo=(Entrega.TipoEntrega.DESPACHO
                          if datos['tipo_entrega'] == 'despacho'
                          else Entrega.TipoEntrega.RETIRO),
                    estado=Entrega.EstadoEntrega.PREPARANDO,
                    direccion_entrega=(datos['direccion']
                                       if datos['tipo_entrega'] == 'despacho'
                                       else 'Retiro en tienda'),
                )
            carrito_ayuda.vaciar_carrito(request)
            messages.success(request,
                             f'Venta #{venta.id} creada. Sigue con el pago.')
            return redirect('webpay:iniciar', venta_id=venta.id)
    else:
        form = CheckoutForm(initial={'direccion': cliente.direccion})

    return render(request, 'tiendaApp/checkout.html', {
        'form': form,
        'lineas': lineas,
        'total': total,
        'neto': round(total / 1.19),
        'iva': total - round(total / 1.19),
    })


@login_required
def mis_compras(request):
    """Listado de ventas web del cliente. Desde aquí puede pagar (o
    reintentar el pago de) las que quedaron PENDIENTES."""
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente is None:
        messages.error(request, 'Tu usuario no tiene perfil de cliente.')
        return redirect('tiendaApp:home')

    ventas = (cliente.ventas
              .prefetch_related('detalles__producto', 'pagos'))
    return render(request, 'tiendaApp/mis_compras.html', {'ventas': ventas})


def _puede_ver_venta(user, venta):
    """Protección de acceso al detalle de una venta:
      - staff: todas
      - vendedor: sus ventas POS y los pedidos web (los atiende en tienda)
      - cliente: SOLO las suyas (RNF-14: nada de datos ajenos)
    """
    if user.is_staff:
        return True
    if hasattr(user, 'vendedor_perfil'):
        return (venta.origen == OrigenVenta.WEB
                or venta.vendedor_id == user.vendedor_perfil.pk)
    cliente = getattr(user, 'cliente_perfil', None)
    return cliente is not None and venta.cliente_id == cliente.pk


@login_required
def detalle_venta(request, venta_id):
    """Detalle completo de una venta: líneas, pagos, entrega y estado.
    Lo usan el cliente (dueño), el vendedor y el administrador."""
    venta = get_object_or_404(
        Venta.objects.prefetch_related('detalles__producto', 'pagos'),
        pk=venta_id)

    if not _puede_ver_venta(request.user, venta):
        messages.error(request, 'No tienes acceso a esa venta.')
        return redirect('tiendaApp:home')

    puede_pagar = (request.user == getattr(venta.cliente,
                                           'usuario_auth', None)
                   and venta.origen == OrigenVenta.WEB
                   and venta.estado == EstadoVenta.PENDIENTE
                   and venta.pago_autorizado is None)

    return render(request, 'tiendaApp/detalle_venta.html', {
        'venta': venta,
        'puede_pagar': puede_pagar,
    })


# =====================================================================
# 6. MÓDULO VENDEDOR (RF-17, RF-18, RF-20, RF-24) + ADMIN (RF-12)
# =====================================================================
def vendedor_requerido(view):
    """Decorador: exige sesión Y perfil de vendedor. Un cliente o un admin
    que entre a estas páginas recibe un mensaje amable, no un error 500."""
    @wraps(view)
    @login_required
    def _wrap(request, *args, **kwargs):
        if not hasattr(request.user, 'vendedor_perfil'):
            messages.error(request, 'Esta sección es solo para vendedores.')
            return redirect('tiendaApp:home')
        return view(request, *args, **kwargs)
    return _wrap


def solo_staff(view):
    """Decorador para 'crear vendedor' (RF-12): solo administradores."""
    @wraps(view)
    @login_required
    @user_passes_test(lambda u: u.is_staff,
                      login_url='login')
    def _wrap(request, *args, **kwargs):
        return view(request, *args, **kwargs)
    return _wrap


@vendedor_requerido
def panel_vendedor(request):
    """Panel del vendedor: jornada activa, resumen del día, alertas de stock
    bajo (RF-17) y pedidos web pendientes de entrega (RF-20)."""
    vendedor = request.user.vendedor_perfil
    jornada = JornadaLaboral.objects.filter(vendedor=vendedor,
                                            fin__isnull=True).first()

    # Ventas POS de HOY del vendedor (cuadre de caja rápido)
    inicio_hoy = timezone.now().replace(hour=0, minute=0, second=0,
                                        microsecond=0)
    ventas_hoy = (Venta.objects
                  .filter(vendedor=vendedor,
                          origen=OrigenVenta.POS,
                          fecha_venta__gte=inicio_hoy,
                          estado=EstadoVenta.COMPLETADA))

    # RF-17 / A-01: productos con stock total <= umbral mínimo.
    # stock_total es una property del modelo (no existe como columna), así
    # que el filtrado se hace en Python: para el volumen de una tienda
    # "demo" es más que suficiente.
    stock_bajo = [s for s in Stock.objects.select_related('producto')
                  if s.producto.activo and s.stock_total <= s.stock_minimo]

    pedidos_pendientes = (Entrega.objects
                          .filter(venta__origen=OrigenVenta.WEB,
                                  venta__estado=EstadoVenta.COMPLETADA)
                          .exclude(estado=Entrega.EstadoEntrega.ENTREGADO)
                          .count())

    return render(request, 'tiendaApp/panel_vendedor.html', {
        'jornada': jornada,
        'resumen_jornada': jornada.resumen_turno() if jornada else None,
        'n_ventas_hoy': ventas_hoy.count(),
        'monto_hoy': sum(v.total for v in ventas_hoy),
        'stock_bajo': stock_bajo,
        'pedidos_pendientes': pedidos_pendientes,
    })


@vendedor_requerido
def pos_nueva_venta(request):
    """RF-18: registro de venta presencial (POS).

    GET : tabla de productos con un input de cantidad por fila.
    POST: lee 'cant_<id>' de cada producto, valida contra el stock total,
          crea la Venta (origen POS) + sus detalles y registra el Pago
          AUTORIZADO. Pago.save() hace la magia: deja la venta COMPLETADA
          y descuenta el stock (mismo camino que WebPay: una sola regla).
    """
    vendedor = request.user.vendedor_perfil
    productos = (Producto.objects
                 .filter(activo=True)
                 .select_related('stock')
                 .order_by('nombre'))

    if request.method == 'POST':
        form = POSVentaForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revisa los datos de la venta.')
            return redirect('tiendaApp:pos_venta')

        # ---- 1) Reúne las líneas pedidas y valida stock ANTES de crear nada
        lineas = []
        for producto in productos:
            try:
                cantidad = int(request.POST.get(f'cant_{producto.pk}', 0) or 0)
            except ValueError:
                cantidad = 0
            if cantidad > 0:
                disponible = _stock_disponible(producto)
                if cantidad > disponible:
                    messages.error(
                        request,
                        f'Stock insuficiente de "{producto.nombre}": '
                        f'pediste {cantidad} y hay {disponible}.')
                    return redirect('tiendaApp:pos_venta')
                lineas.append((producto, cantidad))

        if not lineas:
            messages.warning(request,
                             'No marcaste ningún producto: la venta quedaría '
                             'en $0.')
            return redirect('tiendaApp:pos_venta')

        # ---- 2) Cliente opcional por correo (si tiene cuenta)
        cliente = None
        correo = form.cleaned_data.get('correo_cliente')
        if correo:
            cliente = Cliente.objects.filter(correo__iexact=correo).first()
            if cliente is None:
                messages.warning(request,
                                 'No hay cliente con ese correo: la venta se '
                                 'registra como consumidor final.')

        # ---- 3) Crea la venta + detalles + pago autorizado (atómico)
        with transaction.atomic():
            venta = Venta.objects.create(
                origen=OrigenVenta.POS,
                vendedor=vendedor,
                cliente=cliente,
                estado=EstadoVenta.PENDIENTE,
                tipo_documento=form.cleaned_data['tipo_documento'],
                rut_factura=form.cleaned_data.get('rut_factura'),
                razon_social=form.cleaned_data.get('razon_social'),
            )
            for producto, cantidad in lineas:
                venta.agregar_producto(producto, cantidad)

            # El pago nace AUTORIZADO (se cobró en la caja física).
            # Pago.save() -> venta COMPLETADA + descontar_stock().
            Pago.objects.create(
                venta=venta,
                cliente=cliente,
                vendedor=vendedor,
                medio_pago=form.cleaned_data['medio_pago'],
                monto=venta.total,
                estado_pago=EstadoPago.AUTORIZADO,
            )

        messages.success(request,
                         f'Venta #{venta.id} registrada: ${venta.total} '
                         f'({venta.pago_autorizado.get_medio_pago_display()}).')
        return redirect('tiendaApp:detalle_venta', venta_id=venta.id)

    # GET: formulario vacío + productos con su stock
    return render(request, 'tiendaApp/pos_venta.html', {
        'form': POSVentaForm(),
        'productos': productos,
    })


@vendedor_requerido
def ventas_lista(request):
    """Registro de ventas para el vendedor: sus ventas POS + los pedidos web
    (RF-20). El staff ve TODO. Filtro opcional por estado (?estado=)."""
    vendedor = request.user.vendedor_perfil
    ventas = (Venta.objects
              .filter(Q(origen=OrigenVenta.WEB) | Q(vendedor=vendedor))
              .prefetch_related('detalles__producto', 'pagos'))

    estado = request.GET.get('estado', '')
    if estado:
        ventas = ventas.filter(estado=estado)

    return render(request, 'tiendaApp/ventas.html', {
        'ventas': ventas,
        'estado_actual': estado,
        'estados': EstadoVenta.choices,
    })


@vendedor_requerido
def entregas(request):
    """RF-20: pedidos web pendientes. El vendedor busca el pedido, revisa el
    detalle y avanza el estado de la entrega (preparando -> en_despacho /
    listo_retiro -> entregado)."""
    lista = (Entrega.objects
             .filter(venta__origen=OrigenVenta.WEB)
             .select_related('venta__cliente')
             .exclude(estado=Entrega.EstadoEntrega.ENTREGADO))

    if request.method == 'POST':
        entrega = get_object_or_404(Entrega,
                                    pk=request.POST.get('entrega_id'))
        nuevo = request.POST.get('nuevo_estado')
        validos = Entrega.EstadoEntrega.values
        if nuevo in validos:
            entrega.estado = nuevo
            if nuevo == Entrega.EstadoEntrega.ENTREGADO:
                entrega.fecha_entrega = timezone.now()
            entrega.save(update_fields=['estado', 'fecha_entrega'])
            messages.success(request,
                             f'Entrega #{entrega.id} -> '
                             f'{entrega.get_estado_display()}.')
        else:
            messages.error(request, 'Estado no válido.')
        return redirect('tiendaApp:entregas')

    return render(request, 'tiendaApp/entregas.html', {
        'entregas': lista,
        'estados_entrega': Entrega.EstadoEntrega.choices,
    })


@vendedor_requerido
def jornadas(request):
    """RF-24: jornadas laborales. El vendedor marca ENTRADA (abre jornada)
    y SALIDA (cierra). Al cerrar (o al verla en vivo) aparece el resumen
    del turno: n° de ventas, total recaudado y desglose por medio de pago.
    """
    vendedor = request.user.vendedor_perfil

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'abrir':
            JornadaLaboral.abrir(vendedor)  # no duplica si ya hay una activa
            messages.success(request, 'Jornada iniciada. ¡Buen turno!')
            return redirect('tiendaApp:jornadas')
        if accion == 'cerrar':
            jornada = (JornadaLaboral.objects
                       .filter(vendedor=vendedor, fin__isnull=True).first())
            if jornada:
                jornada.cerrar(notas=request.POST.get('notas', ''))
                messages.success(request, 'Jornada cerrada. Resumen abajo.')
            return redirect('tiendaApp:jornadas')

    jornadas_list = JornadaLaboral.objects.filter(vendedor=vendedor)
    jornada_activa = jornadas_list.filter(fin__isnull=True).first()
    return render(request, 'tiendaApp/jornadas.html', {
        'jornadas': jornadas_list,
        'jornada_activa': jornada_activa,
        'resumen_activa': (jornada_activa.resumen_turno()
                           if jornada_activa else None),
    })


@solo_staff
def crear_vendedor(request):
    """RF-12: el ADMINISTRADOR crea las cuentas de los vendedores.
    Crea el User (para login) y su perfil Vendedor en un solo paso."""
    if request.method == 'POST':
        form = VendedorForm(request.POST)
        if form.is_valid():
            if User.objects.filter(
                    username=form.cleaned_data['username']).exists():
                form.add_error('username', 'Ese nombre de usuario ya existe.')
            else:
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    first_name=form.cleaned_data['first_name'],
                    password=form.cleaned_data['password'],
                )
                vendedor = form.save(commit=False)
                vendedor.usuario_auth = user
                vendedor.save()
                messages.success(
                    request,
                    f'Vendedor "{user.username}" creado con acceso al panel.')
                return redirect('tiendaApp:crear_vendedor')
    else:
        form = VendedorForm()
    vendedores = Vendedor.objects.select_related('usuario_auth')
    return render(request, 'tiendaApp/crear_vendedor.html', {
        'form': form,
        'vendedores': vendedores,
    })
