from django.urls import path

from . import views, carrito_views

app_name = 'tiendaApp'

urlpatterns = [
    path('', views.home, name='home'),
    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/<int:producto_id>/', views.detalle_producto,
         name='detalle_producto'),

    path('mis-fichas/', views.mis_fichas, name='mis_fichas'),
    path('mis-fichas/nueva/', views.crear_ficha, name='crear_ficha'),
    path('mis-fichas/<int:ficha_id>/editar/', views.editar_ficha,
         name='editar_ficha'),

    # RF-07: registro de clientes (login/logout los da django.contrib.auth
    # en /cuenta/, incluido desde el urls.py del proyecto).
    path('registro/', views.registrar, name='registro'),

    # ---- Carrito + checkout + pedidos (RF-05 / RF-06 / RF-18 / RF-20) ----
    path('carrito/', carrito_views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/',
         carrito_views.agregar_al_carrito, name='agregar_carrito'),
    path('carrito/actualizar/<int:producto_id>/',
         carrito_views.actualizar_linea, name='actualizar_linea'),
    path('carrito/quitar/<int:producto_id>/',
         carrito_views.quitar_linea, name='quitar_linea'),
    path('carrito/checkout/', carrito_views.checkout, name='checkout'),

    path('mis-pedidos/', carrito_views.mis_pedidos, name='mis_pedidos'),
]
