from django.urls import path

from . import views

app_name = 'webpay'

urlpatterns = [
    path('pago/<int:venta_id>/', views.iniciar_pago_webpay, name='iniciar'),
    path('retorno/', views.retorno_webpay, name='retorno'),
]
