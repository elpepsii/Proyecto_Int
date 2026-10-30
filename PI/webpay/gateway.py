"""
gateway.py — La ÚNICA pieza del proyecto que habla con Transbank (sandbox).

Diseño a propósito: este archivo NO importa modelos de Django. Solo sabe
CÓMO hablar con WebPay Plus; views.py decide CUÁNDO crear o confirmar una
transacción. Así puedes leerlo/probarlo sin el resto del proyecto.

Configuración SANDBOX:
  - Códigos de comercio y llave de integración que Transbank entrega PÚBLICOS
    para que todo desarrollador pruebe (NO son secretos).
  - Endpoint: https://webpay3gint.transbank.cl (entorno de pruebas).
  - Para producción se reemplazarían por las credenciales reales del
    comercio afiliado (fuera del alcance de este proyecto académico).
"""

import uuid

from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_type import IntegrationType
from transbank.common.options import WebpayOptions
from transbank.error.transbank_error import TransbankError  # noqa: F401 (re-export útil)
from transbank.webpay.webpay_plus.transaction import Transaction

SANDBOX_OPTIONS = WebpayOptions(
    commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,  # 597055555532
    api_key=IntegrationApiKeys.WEBPAY,
    integration_type=IntegrationType.TEST,               # https://webpay3gint.transbank.cl
)


def crear_transaccion(buy_order, session_id, monto, return_url):
    """Paso 1 del flujo: registra la intención de pago en Transbank.

    Devuelve la tupla (token_ws, url_webpay).
      - token_ws: llave temporal (64 chars) que identifica esta transacción.
      - url_webpay: página de Transbank a la que hay que llevar al cliente.

    monto: entero en CLP (WebPay Plus REST NO acepta decimales).
    """
    respuesta = Transaction(SANDBOX_OPTIONS).create(
        buy_order=buy_order,
        session_id=session_id,
        amount=monto,
        return_url=return_url,
    )
    return respuesta['token'], respuesta['url']


def confirmar_transaccion(token_ws):
    """Paso 3 del flujo: confirma el pago (commit) tras el POST de vuelta.

    Devuelve un DICT con la respuesta de Transbank, ej.:
      {
        'vci': 'TSY', 'amount': 12500, 'status': 'AUTHORIZED',
        'buy_order': 'PS-000012-A1B2C3D4', 'session_id': 'venta-12-...',
        'card_detail': {'card_number': '6623'},   # últimos 4 dígitos
        'transaction_date': '2026-10-31T15:04:05.000Z',
        'authorization_code': '123456',
        'payment_type_code': 'VD',                # VD=débito, VN=crédito sin cuotas...
        'response_code': 0,                       # 0 = autorizado
        'installments_number': 0, 'installments_amount': None,
      }
    response_code != 0 => tarjeta rechazada (ver códigos en la doc de Transbank).
    """
    return Transaction(SANDBOX_OPTIONS).commit(token_ws)


def consultar_transaccion(token_ws):
    """Estado de la transacción según Transbank, SIN confirmar.
    Útil para auditoría o re-sincronizar si el servidor se cae a mitad
    del flujo (no se usa en las vistas básicas)."""
    return Transaction(SANDBOX_OPTIONS).status(token_ws)


# ----------------------------------------------------------- generadores ---
# buy_order: Transbank exige MÁXIMO 26 caracteres alfanuméricos y que sea
# ÚNICA por intento. Formato "PS-000012-A1B2C3D4" (18 chars):
#   PS-        prefijo del proyecto
#   000012     id del Pago en TU base de datos (trazabilidad)
#   A1B2C3D4   tramo aleatorio: garantiza unicidad si reintentas varias veces
def generar_buy_order(pago_id):
    return f"PS-{pago_id:06d}-{uuid.uuid4().hex[:8].upper()}"


def generar_session_id(venta_id):
    """session_id: máximo 61 chars. Sirve para rastrear la sesión del
    comprador en los reportes de Transbank; no es un secreto."""
    return f"venta-{venta_id}-{uuid.uuid4().hex[:12]}"