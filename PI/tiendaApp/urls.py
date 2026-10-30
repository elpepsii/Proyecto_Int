from django.urls import path

from . import views

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
]
