from functools import wraps

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from . import carrito
from .forms import (
    CheckoutForm,
    EditarVendedorForm,
    FichaForm,
    PerfilForm,
    POSVentaForm,
    ProveedorForm,
    ProveedorProductoForm,
    RegistroForm,
    VendedorForm,
)
from .models import (
    Cliente,
    Entrega,
    Especie,
    EstadoPago,
    EstadoVenta,
    Ficha,
    JornadaLaboral,
    OrigenVenta,
    Pago,
    Producto,
    Proveedor,
    Stock,
    TamanoGrano,
    Vendedor,
    Venta,
)

TIPO_JUGUETES_ACCESORIOS = 'juguetes-accesorios'


def home(request):
    productos = Producto.objects.filter(activo=True)
    promociones = productos.filter(precio_oferta__isnull=False)[:4]
    destacados = productos[:8]
    return render(
        request,
        'tiendaApp/home.html',
        {
            'destacados': destacados,
            'promociones': promociones,
            'tipo_juguetes_accesorios': TIPO_JUGUETES_ACCESORIOS,
        },
    )


def lista_productos(request):
    productos = Producto.objects.filter(activo=True).select_related('stock')

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
    campos = {
        'animal': especie,
        'edad_producto': edad,
        'tamano_raza': tamano_raza,
        'tamano_grano': tamano_grano,
    }
    productos = productos.filter(**{campo: valor for campo, valor in campos.items() if valor})
    if tipo == TIPO_JUGUETES_ACCESORIOS:
        productos = productos.filter(
            tipo_producto__in=(Producto.TipoProducto.JUGUETE, Producto.TipoProducto.ACCESORIO)
        )
    elif tipo:
        productos = productos.filter(tipo_producto=tipo)

    if precio_min.isdigit():
        productos = productos.filter(precio__gte=int(precio_min))
    if precio_max.isdigit():
        productos = productos.filter(precio__lte=int(precio_max))

    ficha = None
    cliente = getattr(request.user, 'cliente_perfil', None)
    fichas_cliente = cliente.fichas_mascotas.all() if cliente else []
    if cliente and ficha_id:
        ficha = fichas_cliente.filter(pk=ficha_id).first()
    if ficha:
        productos = productos.filter(animal=ficha.especie)
        if ficha.tamano_grano_preferido:
            productos = productos.filter(
                Q(tamano_grano=ficha.tamano_grano_preferido) | Q(tamano_grano__isnull=True)
            )
        productos = productos.exclude(alergenos_contenidos__in=ficha.alergias.all())

    ordenes = {
        'nombre': 'nombre',
        'precio_asc': 'precio',
        'precio_desc': '-precio',
    }
    productos = productos.order_by(ordenes.get(orden, 'nombre'))

    paginator = Paginator(productos, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    filtros = request.GET.copy()
    filtros.pop('page', None)

    return render(
        request,
        'tiendaApp/lista_productos.html',
        {
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
            'tipos': [
                *Producto.TipoProducto.choices,
                (TIPO_JUGUETES_ACCESORIOS, 'Juguetes y accesorios'),
            ],
            'edades': Producto.EtapaVida.choices,
            'razas': Producto.TamanoRaza.choices,
            'granos': TamanoGrano.choices,
            'querystring': filtros.urlencode(),
        },
    )


def detalle_producto(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.select_related('stock'), pk=producto_id, activo=True
    )

    return render(
        request,
        'tiendaApp/detalle_producto.html',
        {
            'producto': producto,
            'stock': getattr(producto, 'stock', None),
            'tamanos_grano': (
                TamanoGrano.choices if producto.tipo_producto == Producto.TipoProducto.ALIMENTO else ()
            ),
        },
    )


@staff_member_required(login_url='login')
@permission_required('tiendaApp.change_proveedor', raise_exception=True)
@require_http_methods(['GET', 'POST'])
def gestion_productos(request):
    if request.method == 'POST':
        form = ProveedorProductoForm(request.POST)
        if form.is_valid() and 'proveedor' in request.POST:
            proveedor = form.cleaned_data['proveedor']
            with transaction.atomic():
                producto = get_object_or_404(
                    Producto.objects.select_for_update(), pk=form.cleaned_data['producto_id']
                )
                producto.proveedores.set([proveedor] if proveedor else [])
            messages.success(request, f'Proveedor actualizado para {producto.nombre}.')
        else:
            messages.error(request, 'Elige un proveedor válido o selecciona «Sin proveedor».')
        return redirect('tiendaApp:gestion_productos')

    return render(
        request,
        'tiendaApp/gestion_productos.html',
        {
            'productos': Producto.objects.prefetch_related('proveedores'),
            'proveedores': Proveedor.objects.all(),
        },
    )


@staff_member_required(login_url='login')
@permission_required('tiendaApp.change_proveedor', raise_exception=True)
def gestionar_proveedores(request):
    return render(
        request, 'tiendaApp/gestionar_proveedores.html', {'proveedores': Proveedor.objects.all()}
    )


@staff_member_required(login_url='login')
@permission_required('tiendaApp.change_proveedor', raise_exception=True)
@require_http_methods(['GET', 'POST'])
def editar_proveedor(request, proveedor_id=None):
    if proveedor_id is None and not request.user.has_perm('tiendaApp.add_proveedor'):
        raise PermissionDenied

    proveedor = get_object_or_404(Proveedor, pk=proveedor_id) if proveedor_id is not None else None
    form = ProveedorForm(request.POST if request.method == 'POST' else None, instance=proveedor)
    if form.is_valid():
        form.save()
        messages.success(request, 'Proveedor guardado.')
        return redirect('tiendaApp:gestionar_proveedores')
    return render(
        request, 'tiendaApp/formulario_proveedor.html', {'form': form, 'proveedor': proveedor}
    )


@login_required
def mis_fichas(request):
    cliente = getattr(request.user, 'cliente_perfil', None)
    fichas = cliente.fichas_mascotas.all() if cliente else []
    return render(request, 'tiendaApp/mis_fichas.html', {'fichas': fichas})


@login_required
def crear_ficha(request):
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente is None:
        messages.error(request, 'Solo los clientes tienen fichas de mascota.')
        return redirect('tiendaApp:home')

    form = FichaForm(request.POST if request.method == 'POST' else None)
    if form.is_valid():
        if cliente.fichas_mascotas.count() >= 20:
            form.add_error(None, 'Tu cuenta ya tiene el máximo de 20 fichas de mascota (RNF-15).')
        else:
            ficha = form.save(commit=False)
            ficha.cliente = cliente
            ficha.save()
            form.save_m2m()
            messages.success(request, f'Ficha de {ficha.nombre} creada.')
            return redirect('tiendaApp:mis_fichas')
    return render(request, 'tiendaApp/ficha_form.html', {'form': form})


@login_required
def editar_ficha(request, ficha_id):
    ficha = get_object_or_404(Ficha, pk=ficha_id, cliente__usuario_auth=request.user)

    form = FichaForm(request.POST if request.method == 'POST' else None, instance=ficha)
    if form.is_valid():
        form.save()
        messages.success(request, 'Ficha actualizada.')
        return redirect('tiendaApp:mis_fichas')
    return render(request, 'tiendaApp/ficha_form.html', {'form': form, 'ficha': ficha})


def registrar(request):
    if request.user.is_authenticated:
        return redirect('tiendaApp:home')

    form = RegistroForm(request.POST if request.method == 'POST' else None)
    if form.is_valid():
        user = form.save()
        Cliente.objects.create(
            usuario_auth=user,
            apellido=form.cleaned_data['apellido'],
            correo=form.cleaned_data['email'],
            telefono=form.cleaned_data['telefono'] or None,
            direccion=form.cleaned_data['direccion'],
        )
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(
            request, f'¡Bienvenido/a, {user.get_full_name()}! Tu cuenta de cliente está lista.'
        )
        return redirect('tiendaApp:home')
    return render(request, 'registration/registro.html', {'form': form})


@login_required
def perfil(request):
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente is None:
        messages.error(request, 'Tu usuario no tiene perfil de cliente.')
        return redirect('tiendaApp:home')

    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            request.user.first_name = form.cleaned_data['first_name']
            request.user.email = form.cleaned_data['email']
            request.user.save(update_fields=['first_name', 'email'])
            messages.success(request, 'Perfil actualizado.')
            return redirect('tiendaApp:perfil')
    else:
        form = PerfilForm(
            instance=cliente,
            initial={
                'first_name': request.user.first_name,
                'email': request.user.email,
            },
        )
    return render(request, 'tiendaApp/perfil.html', {'form': form})


def _leer_cantidad(request):
    try:
        return max(1, int(request.POST.get('cantidad', 1)))
    except (TypeError, ValueError):
        return 1


def _stock_disponible(producto):
    stock = getattr(producto, 'stock', None)
    return stock.stock_total if stock else 0


@require_POST
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id, activo=True)
    cantidad = _leer_cantidad(request)
    disponible = _stock_disponible(producto)

    el_carrito = carrito.obtener_carrito(request)
    clave = str(producto.pk)
    solicitada = int(el_carrito.get(clave, 0)) + cantidad

    nueva_cantidad = min(solicitada, disponible)
    if nueva_cantidad <= 0:
        messages.error(request, f'"{producto.nombre}" no tiene stock disponible.')
        return redirect('tiendaApp:ver_carrito')

    el_carrito[clave] = nueva_cantidad
    carrito.guardar_carrito(request, el_carrito)
    if nueva_cantidad < solicitada:
        messages.warning(
            request,
            f'Solo hay {disponible} unidades de "{producto.nombre}". Se ajustó la cantidad.',
        )
    else:
        messages.success(request, f'Agregado al carrito: {producto.nombre} × {cantidad}.')

    return redirect('tiendaApp:ver_carrito')


@require_POST
def actualizar_linea(request, producto_id):
    el_carrito = carrito.obtener_carrito(request)
    clave = str(producto_id)
    if clave not in el_carrito:
        return redirect('tiendaApp:ver_carrito')

    producto = get_object_or_404(Producto, pk=producto_id)
    disponible = _stock_disponible(producto)
    cantidad = min(_leer_cantidad(request), disponible)

    if cantidad <= 0:
        del el_carrito[clave]
        messages.warning(
            request, f'Sin stock de "{producto.nombre}": el producto se quitó del carrito.'
        )
    else:
        el_carrito[clave] = cantidad

    carrito.guardar_carrito(request, el_carrito)
    return redirect('tiendaApp:ver_carrito')


@require_POST
def quitar_linea(request, producto_id):
    el_carrito = carrito.obtener_carrito(request)
    clave = str(producto_id)
    if clave in el_carrito:
        del el_carrito[clave]
        carrito.guardar_carrito(request, el_carrito)
        messages.info(request, 'Producto quitado del carrito.')
    return redirect('tiendaApp:ver_carrito')


@require_POST
def vaciar_carrito(request):
    carrito.vaciar_carrito(request)
    messages.info(request, 'Carrito vaciado.')
    return redirect('tiendaApp:ver_carrito')


def ver_carrito(request):
    lineas, total = carrito.resumen_carrito(carrito.obtener_carrito(request))
    neto = round(total / 1.19)
    return render(
        request,
        'tiendaApp/carrito.html',
        {
            'lineas': lineas,
            'total': total,
            'neto': neto,
            'iva': total - neto,
        },
    )


@login_required
def checkout(request):
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente is None:
        messages.error(
            request,
            'Tu usuario no tiene perfil de cliente (¿entraste '
            'como vendedor o administrador?). Solo los clientes '
            'compran por la web.',
        )
        return redirect('tiendaApp:home')

    lineas, total = carrito.resumen_carrito(carrito.obtener_carrito(request))
    if not lineas:
        messages.warning(request, 'Tu carrito está vacío.')
        return redirect('tiendaApp:ver_carrito')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            tipo_entrega = datos['tipo_entrega']
            direccion = (
                datos['direccion']
                if tipo_entrega == Entrega.TipoEntrega.DESPACHO
                else 'Retiro en tienda'
            )
            with transaction.atomic():
                venta = Venta.objects.create(
                    origen=OrigenVenta.WEB,
                    cliente=cliente,
                    tipo_documento=datos['tipo_documento'],
                    rut_factura=datos.get('rut_factura'),
                    razon_social=datos.get('razon_social'),
                )
                for linea in lineas:
                    venta.agregar_producto(linea['producto'], linea['cantidad'])
                Entrega.objects.create(
                    venta=venta,
                    tipo=tipo_entrega,
                    direccion_entrega=direccion,
                )
            carrito.vaciar_carrito(request)
            messages.success(request, f'Venta #{venta.id} creada. Sigue con el pago.')
            return redirect('webpay:iniciar', venta_id=venta.id)
    else:
        form = CheckoutForm(initial={'direccion': cliente.direccion})

    neto = round(total / 1.19)
    return render(
        request,
        'tiendaApp/checkout.html',
        {
            'form': form,
            'lineas': lineas,
            'total': total,
            'neto': neto,
            'iva': total - neto,
        },
    )


@login_required
def mis_compras(request):
    cliente = getattr(request.user, 'cliente_perfil', None)
    if cliente is None:
        messages.error(request, 'Tu usuario no tiene perfil de cliente.')
        return redirect('tiendaApp:home')

    ventas = cliente.ventas.prefetch_related('detalles__producto', 'pagos')
    return render(request, 'tiendaApp/mis_compras.html', {'ventas': ventas})


def _puede_ver_venta(user, venta):
    if user.is_staff:
        return True
    if hasattr(user, 'vendedor_perfil'):
        return venta.origen == OrigenVenta.WEB or venta.vendedor_id == user.vendedor_perfil.pk
    cliente = getattr(user, 'cliente_perfil', None)
    return cliente is not None and venta.cliente_id == cliente.pk


@login_required
def detalle_venta(request, venta_id):
    venta = get_object_or_404(
        Venta.objects.prefetch_related('detalles__producto', 'pagos'), pk=venta_id
    )

    if not _puede_ver_venta(request.user, venta):
        messages.error(request, 'No tienes acceso a esa venta.')
        return redirect('tiendaApp:home')

    puede_pagar = (
        request.user == getattr(venta.cliente, 'usuario_auth', None)
        and venta.origen == OrigenVenta.WEB
        and venta.estado == EstadoVenta.PENDIENTE
        and venta.pago_autorizado is None
    )

    return render(
        request,
        'tiendaApp/detalle_venta.html',
        {
            'venta': venta,
            'puede_pagar': puede_pagar,
        },
    )


def vendedor_requerido(view):
    @wraps(view)
    @login_required
    def _wrap(request, *args, **kwargs):
        if not hasattr(request.user, 'vendedor_perfil'):
            messages.error(request, 'Esta sección es solo para vendedores.')
            return redirect('tiendaApp:home')
        return view(request, *args, **kwargs)

    return _wrap


@vendedor_requerido
def panel_vendedor(request):
    vendedor = request.user.vendedor_perfil
    jornada = JornadaLaboral.objects.filter(vendedor=vendedor, fin__isnull=True).first()

    inicio_hoy = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    ventas_hoy = Venta.objects.filter(
        vendedor=vendedor,
        origen=OrigenVenta.POS,
        fecha_venta__gte=inicio_hoy,
        estado=EstadoVenta.COMPLETADA,
    )

    stock_bajo = [
        s
        for s in Stock.objects.select_related('producto')
        if s.producto.activo and s.stock_total <= s.stock_minimo
    ]

    pedidos_pendientes = (
        Entrega.objects.filter(venta__origen=OrigenVenta.WEB, venta__estado=EstadoVenta.COMPLETADA)
        .exclude(estado=Entrega.EstadoEntrega.ENTREGADO)
        .count()
    )

    return render(
        request,
        'tiendaApp/panel_vendedor.html',
        {
            'jornada': jornada,
            'n_ventas_hoy': ventas_hoy.count(),
            'monto_hoy': sum(v.total for v in ventas_hoy),
            'stock_bajo': stock_bajo,
            'pedidos_pendientes': pedidos_pendientes,
        },
    )


@vendedor_requerido
def pos_nueva_venta(request):
    vendedor = request.user.vendedor_perfil
    productos = Producto.objects.filter(activo=True).select_related('stock').order_by('nombre')

    if request.method == 'POST':
        form = POSVentaForm(request.POST)
        if not form.is_valid():
            for producto in productos:
                producto.cantidad_pos = request.POST.get(f'cant_{producto.pk}', 0)
            return render(request, 'tiendaApp/pos_venta.html', {'form': form, 'productos': productos})

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
                        f'pediste {cantidad} y hay {disponible}.',
                    )
                    return redirect('tiendaApp:pos_venta')
                lineas.append((producto, cantidad))

        if not lineas:
            messages.warning(request, 'No marcaste ningún producto: la venta quedaría en $0.')
            return redirect('tiendaApp:pos_venta')

        cliente = None
        correo = form.cleaned_data.get('correo_cliente')
        if correo:
            cliente = Cliente.objects.filter(correo__iexact=correo).first()
            if cliente is None:
                messages.warning(
                    request,
                    'No hay cliente con ese correo: la venta se registra como consumidor final.',
                )

        with transaction.atomic():
            venta = Venta.objects.create(
                origen=OrigenVenta.POS,
                vendedor=vendedor,
                cliente=cliente,
                tipo_documento=form.cleaned_data['tipo_documento'],
                rut_factura=form.cleaned_data.get('rut_factura'),
                razon_social=form.cleaned_data.get('razon_social'),
            )
            for producto, cantidad in lineas:
                venta.agregar_producto(producto, cantidad)

            Pago.objects.create(
                venta=venta,
                cliente=cliente,
                vendedor=vendedor,
                medio_pago=form.cleaned_data['medio_pago'],
                monto=venta.total,
                estado_pago=EstadoPago.AUTORIZADO,
            )

        messages.success(
            request,
            f'Venta #{venta.id} registrada: ${venta.total} '
            f'({venta.pago_autorizado.get_medio_pago_display()}).',
        )
        return redirect('tiendaApp:detalle_venta', venta_id=venta.id)

    return render(
        request,
        'tiendaApp/pos_venta.html',
        {
            'form': POSVentaForm(),
            'productos': productos,
        },
    )


@vendedor_requerido
def ventas_lista(request):
    vendedor = request.user.vendedor_perfil
    ventas = Venta.objects.filter(
        Q(origen=OrigenVenta.WEB) | Q(vendedor=vendedor)
    ).prefetch_related('detalles__producto', 'pagos')

    estado = request.GET.get('estado', '')
    if estado:
        ventas = ventas.filter(estado=estado)

    return render(
        request,
        'tiendaApp/ventas.html',
        {
            'ventas': ventas,
            'estado_actual': estado,
            'estados': EstadoVenta.choices,
        },
    )


@vendedor_requerido
def entregas(request):
    lista = (
        Entrega.objects.filter(venta__origen=OrigenVenta.WEB)
        .select_related('venta__cliente')
        .exclude(estado=Entrega.EstadoEntrega.ENTREGADO)
    )

    if request.method == 'POST':
        entrega = get_object_or_404(Entrega, pk=request.POST.get('entrega_id'))
        nuevo = request.POST.get('nuevo_estado')
        if nuevo in Entrega.EstadoEntrega.values:
            entrega.estado = nuevo
            if nuevo == Entrega.EstadoEntrega.ENTREGADO:
                entrega.fecha_entrega = timezone.now()
            entrega.save(update_fields=['estado', 'fecha_entrega'])
            messages.success(request, f'Entrega #{entrega.id} -> {entrega.get_estado_display()}.')
        else:
            messages.error(request, 'Estado no válido.')
        return redirect('tiendaApp:entregas')

    return render(
        request,
        'tiendaApp/entregas.html',
        {
            'entregas': lista,
            'estados_entrega': Entrega.EstadoEntrega.choices,
        },
    )


@vendedor_requerido
def jornadas(request):
    vendedor = request.user.vendedor_perfil

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'abrir':
            JornadaLaboral.abrir(vendedor)
            messages.success(request, 'Jornada iniciada. ¡Buen turno!')
            return redirect('tiendaApp:jornadas')
        if accion == 'cerrar':
            jornada = JornadaLaboral.objects.filter(vendedor=vendedor, fin__isnull=True).first()
            if jornada:
                jornada.cerrar(notas=request.POST.get('notas', ''))
                messages.success(request, 'Jornada cerrada. Resumen abajo.')
            return redirect('tiendaApp:jornadas')

    jornadas_list = JornadaLaboral.objects.filter(vendedor=vendedor)
    jornada_activa = jornadas_list.filter(fin__isnull=True).first()
    return render(
        request,
        'tiendaApp/jornadas.html',
        {
            'jornadas': jornadas_list,
            'jornada_activa': jornada_activa,
            'resumen_activa': (jornada_activa.resumen_turno() if jornada_activa else None),
        },
    )


@staff_member_required(login_url='login')
def crear_vendedor(request):
    if request.method == 'POST':
        form = VendedorForm(request.POST)
        if form.is_valid():
            if User.objects.filter(username=form.cleaned_data['username']).exists():
                form.add_error('username', 'Ese nombre de usuario ya existe.')
            else:
                with transaction.atomic():
                    vendedor = form.save(commit=False)
                    vendedor.usuario_auth = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        password=form.cleaned_data['password'],
                    )
                    vendedor.save()
                user = vendedor.usuario_auth
                messages.success(request, f'Vendedor "{user.username}" creado con acceso al panel.')
                return redirect('tiendaApp:gestionar_vendedores')
    else:
        form = VendedorForm()
    return render(request, 'tiendaApp/crear_vendedor.html', {'form': form})


@staff_member_required(login_url='login')
def gestionar_vendedores(request):
    vendedores = Vendedor.objects.select_related('usuario_auth').order_by('usuario_auth__username')
    return render(request, 'tiendaApp/gestionar_vendedores.html', {'vendedores': vendedores})


@staff_member_required(login_url='login')
def editar_vendedor(request, vendedor_id):
    vendedor = get_object_or_404(Vendedor.objects.select_related('usuario_auth'), pk=vendedor_id)
    usuario = vendedor.usuario_auth
    form = EditarVendedorForm(
        request.POST if request.method == 'POST' else None,
        instance=vendedor,
        initial={'first_name': usuario.first_name, 'last_name': usuario.last_name},
    )
    if form.is_valid():
        with transaction.atomic():
            form.save()
            usuario.first_name = form.cleaned_data['first_name']
            usuario.last_name = form.cleaned_data['last_name']
            usuario.save(update_fields=['first_name', 'last_name'])
        messages.success(request, f'Vendedor "{usuario.username}" actualizado.')
        return redirect('tiendaApp:gestionar_vendedores')
    return render(request, 'tiendaApp/crear_vendedor.html', {'form': form, 'vendedor': vendedor})
