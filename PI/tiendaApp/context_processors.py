from . import carrito as carrito_ayuda


def carrito_cantidad(request):
    el_carrito = carrito_ayuda.obtener_carrito(request)
    return {'cantidad_carrito': sum(int(n) for n in el_carrito.values())}
