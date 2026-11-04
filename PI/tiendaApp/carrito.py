"""
carrito.py — Ayudante del carrito de compras (RF-05).

El carrito vive en la SESIÓN del visitante (request.session): un diccionario
simple {id_producto(str): cantidad}. No necesita login ni tablas nuevas:
Django lo guarda automáticamente entre una página y la siguiente.

¿Por qué un módulo aparte y no dentro de views.py?
  - views.py ORQUESTA (recibe el request, responde una página).
  - Aquí vive el "cómo se guarda y se lee" el carrito: lógica reutilizable
    que necesitan varias vistas (agregar, ver, checkout...).
"""

from .models import Producto

# Nombre con el que el carrito se guarda dentro de request.session
CLAVE_SESION = 'carrito'


def obtener_carrito(request):
    """Devuelve el diccionario del carrito, ej: {'5': 2, '12': 1}.
    Las claves son SIEMPRE str (así lo exige el serializador de sesión)."""
    return request.session.get(CLAVE_SESION, {})


def guardar_carrito(request, carrito):
    """Persiste el diccionario en la sesión. Si quedó vacío, se elimina."""
    if carrito:
        request.session[CLAVE_SESION] = carrito
    else:
        request.session.pop(CLAVE_SESION, None)
    request.session.modified = True  # fuerza a Django a guardar la sesión


def vaciar_carrito(request):
    """Se usa justo después de crear la Venta en el checkout."""
    guardar_carrito(request, {})


def resumen_carrito(carrito):
    """Convierte el diccionario de la sesión en líneas listas para mostrar
    o para armar la Venta. Devuelve (lineas, total).

    Cada línea es un dict: {'producto': <Producto>, 'cantidad': int,
    'subtotal': int}. Los productos borrados o desactivados mientras tanto
    se ignoran automáticamente (nunca entrarían a la venta).
    """
    lineas = []
    total = 0
    productos = Producto.objects.filter(id__in=carrito.keys(), activo=True)
    for producto in productos:
        cantidad = int(carrito.get(str(producto.pk), 0))
        if cantidad <= 0:
            continue
        subtotal = producto.precio * cantidad
        lineas.append({'producto': producto,
                       'cantidad': cantidad,
                       'subtotal': subtotal})
        total += subtotal
    return lineas, total
