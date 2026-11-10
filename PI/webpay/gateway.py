import uuid

from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_type import IntegrationType
from transbank.common.options import WebpayOptions
from transbank.webpay.webpay_plus.transaction import Transaction

SANDBOX_OPTIONS = WebpayOptions(
    commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
    api_key=IntegrationApiKeys.WEBPAY,
    integration_type=IntegrationType.TEST,
)


def crear_transaccion(buy_order, session_id, monto, return_url):
    respuesta = Transaction(SANDBOX_OPTIONS).create(
        buy_order=buy_order,
        session_id=session_id,
        amount=monto,
        return_url=return_url,
    )
    return respuesta['token'], respuesta['url']


def confirmar_transaccion(token_ws):
    return Transaction(SANDBOX_OPTIONS).commit(token_ws)


def consultar_transaccion(token_ws):
    """Consulta el estado en Transbank sin confirmar el cobro."""
    return Transaction(SANDBOX_OPTIONS).status(token_ws)


def generar_buy_order(pago_id):
    return f"PS-{pago_id:06d}-{uuid.uuid4().hex[:8].upper()}"


def generar_session_id(venta_id):
    return f"venta-{venta_id}-{uuid.uuid4().hex[:12]}"
