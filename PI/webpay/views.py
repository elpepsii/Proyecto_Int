"""
views.py — Flujo WebPay Plus en 3 pasos (SANDBOX).

  1) iniciar_pago_webpay : crea el Pago (pendiente), registra la transacción
     en Transbank y muestra el "puente" que hace POST automático a WebPay.
  2) (El cliente paga —o cancela— en el sitio de Transbank.)
  3) retorno_webpay      : Transbank hace POST de vuelta a TU servidor con el
     token; aquí se confirma (commit) y se cierra el Pago. La lógica del
     Pago.save() de tu models.py es la que deja la Venta COMPLETADA.

Reparto de responsabilidades (lo conversado sobre el "fat model"):
  - VIEWS de esta app  -> orquestación del flujo externo (cuándo).
  - Pago.save()        -> reglas internas de tu negocio (qué pasa).
  - gateway.py         -> detalle técnico del SDK (cómo hablar con la API).

APP PRINCIPAL: ya configurado para 'tiendaApp'. Si en INSTALLED_APPS la
registraste con otro nombre exacto, cambia SOLO la línea de import de
más abajo (nadie más de este archivo toca rutas ni nombres).
"""

import logging
from datetime import datetime

from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from transbank.error.transbank_error import TransbankError

# ==========================================================================
#  App principal donde viven los modelos. Ya apunta a 'tiendaApp'; si en
#  INSTALLED_APPS la registraste con otro nombre exacto, cambia esta línea.
# ==========================================================================
from tiendaApp.models import Venta, Pago, EstadoPago, EstadoVenta, MedioPago, OrigenVenta

from . import gateway

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ Paso 1
@require_http_methods(["GET"])
def iniciar_pago_webpay(request, venta_id):
    """Crea el intento de pago y redirige al cliente hacia WebPay."""
    venta = get_object_or_404(Venta, pk=venta_id)

    # ---------------- Guardas de negocio (antes de hablar con Transbank) --
    # WebPay es el medio de pago de la tienda online; el POS se cobra con
    # la caja física (débito/crédito/efectivo), nunca aquí.
    if venta.origen != OrigenVenta.WEB:
        return _resultado(request, venta,
                          titulo='Venta no pagable por WebPay',
                          mensaje='Esta venta es de POS y se cobra por la caja física.')

    # Regla de tu constraint unique_pago_autorizado_por_venta: no cobrar 2 veces.
    if venta.pago_autorizado is not None:
        return _resultado(request, venta,
                          titulo='Esta venta ya está pagada',
                          mensaje='Ya existe un pago autorizado para esta venta.')

    if venta.estado != EstadoVenta.PENDIENTE:
        return _resultado(request, venta,
                          titulo='Venta no pagable',
                          mensaje=f'La venta está en estado "{venta.get_estado_display()}" y no admite pagos.')

    if venta.total <= 0:
        return _resultado(request, venta,
                          titulo='Monto inválido',
                          mensaje='La venta no tiene productos o el total es $0.')

    # ---------------- Se registra el INTENTO como Pago (pendiente) --------
    # Snapshot: cliente y monto quedan congelados en el pago, aunque la
    # venta o el precio cambien después. El vendedor queda NULL (venta web).
    pago = Pago.objects.create(
        venta=venta,
        cliente=venta.cliente,
        medio_pago=MedioPago.WEBPAY,
        monto=venta.total,
        estado_pago=EstadoPago.PENDIENTE,
    )

    # buy_order necesita el id del pago recién creado -> se generan ahora.
    buy_order = gateway.generar_buy_order(pago.pk)
    session_id = gateway.generar_session_id(venta.pk)

    # URL ABSOLUTA donde Transbank hará POST al terminar (públicamente
    # alcanzable: en desarrollo local necesitarás ngrok o similar).
    return_url = request.build_absolute_uri(reverse('webpay:retorno'))

    try:
        token_ws, url_webpay = gateway.crear_transaccion(
            buy_order, session_id, venta.total, return_url)
    except TransbankError as e:
        logger.error('WebPay create falló para venta %s: %s', venta.pk, e)
        pago.estado_pago = EstadoPago.FALLIDO
        pago.save()
        return _resultado(request, venta,
                          titulo='No se pudo iniciar el pago',
                          mensaje='Transbank rechazó la creación de la transacción. Intenta nuevamente.')

    # Guardamos el token/orden en el pago para poder reconocerlo al volver
    # (segunda save del mismo pago: create() no llevaba el token aún).
    pago.buy_order = buy_order
    pago.session_id = session_id
    pago.token_ws = token_ws
    pago.save(update_fields=['buy_order', 'session_id', 'token_ws'])

    # Plantilla "puente": form oculto que hace POST automático hacia
    # Transbank con el token. (Es la forma recomendada por Transbank en vez
    # de un redirect GET.)
    return render(request, 'webpay/redirigir_webpay.html',
                  {'url_webpay': url_webpay, 'token_ws': token_ws})


# ------------------------------------------------------------------ Paso 3
@csrf_exempt  # Transbank es un servidor externo: no puede llevar tu CSRF token
@require_http_methods(["POST"])
def retorno_webpay(request):
    """Transbank hace POST aquí al terminar. Dos escenarios posibles:

    A) El cliente ABORTÓ (botón cancelar), el formulario expiró (>10 min)
       o hubo un doble POST: Transbank envía TBK_TOKEN (+ TBK_ORDEN_COMPRA).
    B) El flujo normal: envía token_ws y confirmamos con commit.
    """
    # ---------------- Escenario A: pago abandonado -----------------------
    if 'TBK_TOKEN' in request.POST:
        return _pago_abandonado(request)

    # ---------------- Escenario B: flujo normal --------------------------
    token_ws = request.POST.get('token_ws')
    if not token_ws:
        return _resultado(request, None,
                          titulo='Llamada inválida',
                          mensaje='No llegó ningún token desde Transbank.')

    pago = (Pago.objects
            .filter(token_ws=token_ws)
            .select_related('venta')
            .first())
    if pago is None:
        logger.warning('Retorno WebPay con token desconocido: %s', token_ws[:12])
        return _resultado(request, None,
                          titulo='Transacción no encontrada',
                          mensaje='No existe un pago con ese token en el sistema.')

    # Guard anti doble-POST: Transbank a veces llama DOS veces al retorno.
    # Si este pago ya se resolvió, mostramos su resultado sin re-confirmar
    # (commit doble lanzaría error en Transbank).
    if pago.estado_pago != EstadoPago.PENDIENTE:
        return _resultado(request, pago.venta, pago=pago)

    try:
        r = gateway.confirmar_transaccion(token_ws)
    except TransbankError as e:
        logger.error('WebPay commit falló (pago %s): %s', pago.pk, e)
        pago.estado_pago = EstadoPago.FALLIDO
        pago.save()
        return _resultado(request, pago.venta, pago=pago,
                          titulo='Error al confirmar',
                          mensaje='Transbank no pudo confirmar la transacción. Puedes reintentar.')

    # ------- Conciliación: guardar TODO lo que Transbank respondió -------
    pago.codigo_respuesta = r.get('response_code')
    pago.codigo_autorizacion = r.get('authorization_code') or ''
    pago.tipo_pago = r.get('payment_type_code')      # VD débito / VN crédito sin cuotas...
    pago.cuotas = r.get('installments_number') or 0
    pago.card_last4 = (r.get('card_detail') or {}).get('card_number')
    pago.fecha_transaccion = _parsear_fecha_tbk(r.get('transaction_date'))
    pago.vci = r.get('vci') or ''

    if r.get('response_code') == 0 and r.get('status') == 'AUTHORIZED':
        pago.estado_pago = EstadoPago.AUTORIZADO
    else:
        # Rechazada por el emisor: queda como intento FALLIDO, la venta
        # sigue PENDIENTE y el cliente puede reintentar (nuevo Pago).
        pago.estado_pago = EstadoPago.FALLIDO

    # Pago.save() de tu models.py hace el resto automáticamente: fija
    # fecha_confirmacion y mueve la Venta a COMPLETADA si autorizó.
    pago.save()
    return _resultado(request, pago.venta, pago=pago)


# ----------------------------------------------------------------- helpers
def _pago_abandonado(request):
    """Caso A del retorno: el cliente no terminó el pago (o doble POST)."""
    buy_order = request.POST.get('TBK_ORDEN_COMPRA')
    pago = None
    if buy_order:
        pago = (Pago.objects
                .filter(buy_order=buy_order)
                .select_related('venta')
                .first())
    if pago and pago.estado_pago == EstadoPago.PENDIENTE:
        pago.estado_pago = EstadoPago.FALLIDO
        pago.save()   # la venta sigue PENDIENTE -> se puede reintentar
    return _resultado(request, pago.venta if pago else None, pago=pago,
                      titulo='Pago cancelado',
                      mensaje='No se completó el pago en WebPay. Puedes intentarlo de nuevo cuando quieras.')


def _resultado(request, venta, pago=None, titulo='', mensaje=''):
    """Única plantilla de resultado para todos los casos finales."""
    return render(request, 'webpay/resultado_pago.html', {
        'titulo': titulo,
        'mensaje': mensaje,
        'venta': venta,
        'pago': pago,
        'autorizado': bool(pago and pago.estado_pago == EstadoPago.AUTORIZADO),
        'fallido': bool(pago and pago.estado_pago == EstadoPago.FALLIDO),
    })


def _parsear_fecha_tbk(valor):
    """Transbank manda fechas tipo '2026-10-31T15:04:05.000Z'.
    Si viene rara, guardamos None en vez de romper la confirmación."""
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None