"""
views.py — Vistas de la tienda (home, catálogo, detalle, fichas de mascota).

Observa el reparto que conversamos:
  - Aquí va la ORQUESTACIÓN (qué se muestra, qué filtros lee del GET).
  - Las reglas de negocio siguen viviendo en models.py (agregar_producto,
    calcular_total, etc.). Ninguna vista escribe 'total' ni 'subtotal'.
"""

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FichaForm, RegistroForm
from .models import Cliente, Especie, Ficha, Producto, Stock


# ----------------------------------------------------------------- Tienda
def home(request):
    """Portada: productos activos como destacados."""
    destacados = (Producto.objects
                  .filter(activo=True)
                  .order_by('nombre')[:8])
    return render(request, 'tiendaApp/home.html', {'destacados': destacados})


def lista_productos(request):
    """Catálogo con filtros por GET (especie, tipo, búsqueda) y paginación."""
    productos = (Producto.objects
                 .filter(activo=True)
                 .select_related('stock'))

    especie = request.GET.get('especie', '')
    tipo = request.GET.get('tipo', '')
    q = request.GET.get('q', '')

    if especie:
        productos = productos.filter(animal=especie)
    if tipo:
        productos = productos.filter(tipo_producto=tipo)
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(sku__icontains=q))

    paginator = Paginator(productos.order_by('nombre'), 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Querystring sin 'page', para que los links de paginación conserven
    # los filtros que el usuario ya había elegido.
    filtros = request.GET.copy()
    filtros.pop('page', None)

    return render(request, 'tiendaApp/lista_productos.html', {
        'page_obj': page_obj,
        'q': q,
        'especie_actual': especie,
        'tipo_actual': tipo,
        'especies': Especie.choices,
        'tipos': Producto.TipoProducto.choices,
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


# --------------------------------------------------- Fichas de mascota
@login_required
def mis_fichas(request):
    """Listado de mascotas del cliente logueado.

    cliente_perfil es el related_name de Cliente.usuario_auth (OneToOne):
    desde el User se llega directo a su perfil de cliente.
    """
    cliente = request.user.cliente_perfil
    fichas = cliente.fichas_mascotas.all()
    return render(request, 'tiendaApp/mis_fichas.html', {'fichas': fichas})


@login_required
def crear_ficha(request):
    """Crea una ficha nueva para el cliente logueado.

    favoritos y alergias son M2M: se guardan con save_m2m() DESPUÉS de
    persistir la ficha (Django exige que la fila exista para enlazar).
    """
    cliente = request.user.cliente_perfil
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
            return redirect('tiendaApp:mis_fichas')
    else:
        form = FichaForm(instance=ficha)
    return render(request, 'tiendaApp/ficha_form.html',
                  {'form': form, 'ficha': ficha})


# ------------------------------------------------------ Registro (RF-07)
def registrar(request):
    """Registro de clientes: crea el User (auth) y su perfil Cliente.
    UserCreationForm valida contraseñas; el perfil se crea SOLO si el
    usuario se guardó bien."""
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
            login(request, user)  # queda logueado de inmediato
            return redirect('tiendaApp:home')
    else:
        form = RegistroForm()
    return render(request, 'registration/registro.html', {'form': form})
