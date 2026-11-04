"""
context_processors.py — Inyecta datos en TODAS las plantillas.

Un context processor es una función que Django llama en cada render() y que
agrega variables al contexto global de las plantillas. Este agrega
'cantidad_carrito' para el numerito del carrito en la barra de navegación
(base.html), sin tener que pasarlo vista por vista.

Para activarlo se registra en settings.py -> TEMPLATES -> OPTIONS ->
context_processors (ya quedó agregado en el settings.py de este proyecto).
"""

from . import carrito as carrito_ayuda


def carrito_cantidad(request):
    el_carrito = carrito_ayuda.obtener_carrito(request)
    return {'cantidad_carrito': sum(int(n) for n in el_carrito.values())}
