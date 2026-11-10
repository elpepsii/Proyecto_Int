from .models import Producto

CLAVE_SESION = 'carrito'


def obtener_carrito(request):
    # La sesión serializa las claves de producto como texto.
    return request.session.get(CLAVE_SESION, {})


def guardar_carrito(request, carrito):
    if carrito:
        request.session[CLAVE_SESION] = carrito
    else:
        request.session.pop(CLAVE_SESION, None)
    request.session.modified = True


def vaciar_carrito(request):
    guardar_carrito(request, {})


def resumen_carrito(carrito):
    lineas = []
    total = 0
    productos = Producto.objects.filter(id__in=carrito.keys(), activo=True)
    for producto in productos:
        cantidad = int(carrito.get(str(producto.pk), 0))
        if cantidad <= 0:
            continue
        subtotal = producto.precio * cantidad
        lineas.append({'producto': producto, 'cantidad': cantidad, 'subtotal': subtotal})
        total += subtotal
    return lineas, total
