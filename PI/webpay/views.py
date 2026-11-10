import logging
from datetime import datetime

from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from transbank.error.transbank_error import TransbankError

from tiendaApp.models import (
    EstadoPago,
    EstadoVenta,
    MedioPago,
    OrigenVenta,
    Pago,
    Venta,
)

from . import gateway

logger = logging.getLogger(__name__)


@require_GET
def iniciar_pago_webpay(request, venta_id):
    venta = get_object_or_404(Venta, pk=venta_id)

    if venta.origen != OrigenVenta.WEB:
        return _resultado(
            request,
            venta,
            titulo='Venta no pagable por WebPay',
            mensaje='Esta venta es de POS y se cobra por la caja física.',
        )

    if venta.pago_autorizado is not None:
        return _resultado(
            request,
            venta,
            titulo='Esta venta ya está pagada',
            mensaje='Ya existe un pago autorizado para esta venta.',
        )

    if venta.estado != EstadoVenta.PENDIENTE:
        return _resultado(
            request,
            venta,
            titulo='Venta no pagable',
            mensaje=f'La venta está en estado "{venta.get_estado_display()}" y no admite pagos.',
        )

    if venta.total <= 0:
        return _resultado(
            request,
            venta,
            titulo='Monto inválido',
            mensaje='La venta no tiene productos o el total es $0.',
        )

    pago = Pago.objects.create(
        venta=venta,
        cliente=venta.cliente,
        medio_pago=MedioPago.WEBPAY,
        monto=venta.total,
    )

    buy_order = gateway.generar_buy_order(pago.pk)
    session_id = gateway.generar_session_id(venta.pk)

    return_url = request.build_absolute_uri(reverse('webpay:retorno'))

    try:
        token_ws, url_webpay = gateway.crear_transaccion(
            buy_order, session_id, venta.total, return_url
        )
    except (TransbankError, ValueError) as e:
        logger.error('WebPay create falló para venta %s: %s', venta.pk, e)
        pago.estado_pago = EstadoPago.FALLIDO
        pago.save()
        return _resultado(
            request,
            venta,
            titulo='No se pudo iniciar el pago',
            mensaje='Transbank rechazó la creación de la transacción. Intenta nuevamente.',
        )

    pago.buy_order = buy_order
    pago.session_id = session_id
    pago.token_ws = token_ws
    pago.save(update_fields=['buy_order', 'session_id', 'token_ws'])

    return render(
        request, 'webpay/redirigir_webpay.html', {'url_webpay': url_webpay, 'token_ws': token_ws}
    )


@csrf_exempt  # El retorno externo de Transbank no incluye el token CSRF de Django.
@require_http_methods(['GET', 'POST'])
def retorno_webpay(request):
    datos = request.POST if request.method == 'POST' else request.GET

    if 'TBK_TOKEN' in datos:
        return _pago_abandonado(request, datos)

    token_ws = datos.get('token_ws')
    if not token_ws:
        return _resultado(
            request,
            None,
            titulo='Llamada inválida',
            mensaje='No llegó ningún token desde Transbank.',
        )

    pago = Pago.objects.filter(token_ws=token_ws).select_related('venta').first()
    if pago is None:
        logger.warning('Retorno WebPay con token desconocido: %s', token_ws[:12])
        return _resultado(
            request,
            None,
            titulo='Transacción no encontrada',
            mensaje='No existe un pago con ese token en el sistema.',
        )

    # Una devolución repetida debe mostrar el resultado sin volver a confirmar.
    if pago.estado_pago != EstadoPago.PENDIENTE:
        return _resultado(request, pago.venta, pago=pago)

    try:
        respuesta = gateway.confirmar_transaccion(token_ws)
    except (TransbankError, ValueError) as e:
        logger.error('WebPay commit falló (pago %s): %s', pago.pk, e)
        pago.estado_pago = EstadoPago.FALLIDO
        pago.save()
        return _resultado(
            request,
            pago.venta,
            pago=pago,
            titulo='Error al confirmar',
            mensaje='Transbank no pudo confirmar la transacción. Puedes reintentar.',
        )

    pago.codigo_respuesta = respuesta.get('response_code')
    pago.codigo_autorizacion = respuesta.get('authorization_code') or ''
    pago.tipo_pago = respuesta.get('payment_type_code')
    pago.cuotas = respuesta.get('installments_number') or 0
    pago.card_last4 = (respuesta.get('card_detail') or {}).get('card_number')
    pago.fecha_transaccion = _parsear_fecha_tbk(respuesta.get('transaction_date'))
    pago.vci = respuesta.get('vci') or ''
    autorizado = pago.codigo_respuesta == 0 and respuesta.get('status') == 'AUTHORIZED'
    pago.estado_pago = EstadoPago.AUTORIZADO if autorizado else EstadoPago.FALLIDO

    pago.save()
    return _resultado(request, pago.venta, pago=pago)


def _pago_abandonado(request, datos):
    buy_order = datos.get('TBK_ORDEN_COMPRA')
    pago = None
    if buy_order:
        pago = Pago.objects.filter(buy_order=buy_order).select_related('venta').first()
    if pago and pago.estado_pago == EstadoPago.PENDIENTE:
        pago.estado_pago = EstadoPago.FALLIDO
        pago.save()
    return _resultado(
        request,
        pago.venta if pago else None,
        pago=pago,
        titulo='Pago cancelado',
        mensaje='No se completó el pago en WebPay. Puedes intentarlo de nuevo cuando quieras.',
    )


def _resultado(request, venta, pago=None, titulo='', mensaje=''):
    return render(
        request,
        'webpay/resultado_pago.html',
        {
            'titulo': titulo,
            'mensaje': mensaje,
            'venta': venta,
            'pago': pago,
            'autorizado': bool(pago and pago.estado_pago == EstadoPago.AUTORIZADO),
            'fallido': bool(pago and pago.estado_pago == EstadoPago.FALLIDO),
        },
    )


def _parsear_fecha_tbk(valor):
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None
