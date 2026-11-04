from django.urls import path

from . import views

app_name = 'tiendaApp'

urlpatterns = [
    # ------------------------------------------------ Tienda pública
    path('', views.home, name='home'),
    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/<int:producto_id>/', views.detalle_producto,
         name='detalle_producto'),

    # ------------------------------------------------ RF-07: cuenta
    path('registro/', views.registrar, name='registro'),
    path('perfil/', views.perfil, name='perfil'),

    # ------------------------------------------------ RF-08: fichas
    path('mis-fichas/', views.mis_fichas, name='mis_fichas'),
    path('mis-fichas/nueva/', views.crear_ficha, name='crear_ficha'),
    path('mis-fichas/<int:ficha_id>/editar/', views.editar_ficha,
         name='editar_ficha'),

    # --------------------------------- RF-05 / RF-06: carrito y compra
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito,
         name='agregar_carrito'),
    path('carrito/actualizar/<int:producto_id>/', views.actualizar_linea,
         name='actualizar_linea'),
    path('carrito/quitar/<int:producto_id>/', views.quitar_linea,
         name='quitar_linea'),
    path('carrito/vaciar/', views.vaciar_carrito, name='vaciar_carrito'),
    path('carrito/checkout/', views.checkout, name='checkout'),

    # ------------------------------------------------ Compras del cliente
    path('mis-compras/', views.mis_compras, name='mis_compras'),
    path('ventas/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),

    # ------------------------------------------------ Módulo vendedor
    path('vendedor/', views.panel_vendedor, name='panel_vendedor'),
    path('vendedor/pos/', views.pos_nueva_venta, name='pos_venta'),
    path('vendedor/ventas/', views.ventas_lista, name='ventas_lista'),
    path('vendedor/entregas/', views.entregas, name='entregas'),
    path('vendedor/jornadas/', views.jornadas, name='jornadas'),

    # ------------------------------------------------ RF-12 (solo admin)
    path('vendedores/nuevo/', views.crear_vendedor, name='crear_vendedor'),
]
