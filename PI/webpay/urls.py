from django.urls import path

from . import views

app_name = 'webpay'

urlpatterns = [
    # Paso 1: TU servidor lleva al cliente hacia Transbank
    path('pago/<int:venta_id>/', views.iniciar_pago_webpay, name='iniciar'),

    # Paso 3: Transbank hace POST de vuelta a esta URL (return_url).
    # El nombre 'webpay:retorno' DEBE mantenerse: iniciar_pago_webpay
    # construye el return_url con reverse('webpay:retorno').
    path('retorno/', views.retorno_webpay, name='retorno'),
]