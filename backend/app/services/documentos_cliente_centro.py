"""
Punto de entrada unico para documentos al cliente (estado de cuenta + recibo por pago reportado).

Los modulos de datos/PDF concretos siguen en sus archivos; aqui solo se re-exporta para que
nuevos servicios importen desde un solo sitio. Ver `backend/docs/DOCUMENTOS_CLIENTE_CENTRO_UNICO.md`.
"""
from app.services.cobros.recibo_pago_reportado_centro import (
    generar_recibo_pdf_desde_pago_reportado,
    kwargs_recibo_pago_reportado,
    monto_texto_pago_reportado,
    tasa_bs_usd_para_recibo_pago_reportado,
)
from app.services.estado_cuenta_datos import (
    obtener_datos_estado_cuenta_cliente,
    obtener_datos_estado_cuenta_prestamo,
    obtener_recibos_cliente_estado_cuenta,
    serializar_estado_cuenta_payload_json,
)
from app.services.estado_cuenta_pdf import generar_pdf_estado_cuenta

__all__ = [
    "generar_pdf_estado_cuenta",
    "generar_recibo_pdf_desde_pago_reportado",
    "kwargs_recibo_pago_reportado",
    "monto_texto_pago_reportado",
    "obtener_datos_estado_cuenta_cliente",
    "obtener_datos_estado_cuenta_prestamo",
    "obtener_recibos_cliente_estado_cuenta",
    "serializar_estado_cuenta_payload_json",
    "tasa_bs_usd_para_recibo_pago_reportado",
]
