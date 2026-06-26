"""Alineación de estado de pago con flags de conciliación y post-cascada."""

from app.models.pago import Pago
from app.services.pago_autoconciliacion import (
    marcar_pago_autoconciliado,
    pago_preserva_autoconciliacion_sin_cuotas,
)
from app.services.pago_reescaneo_ocr import sin_documento_real_tras_reocr

from .cascada_estado import _estado_pago_tras_aplicar_cascada


def _alinear_estado_si_toggle_conciliado_actualizar_pago(row: Pago, conciliado_nuevo: bool) -> None:
    """
    Alinea pagos.estado con cambios de conciliado para cumplir CHECKs en BD:
    - conciliado True: no dejar PENDIENTE/otros; pasar a PAGADO salvo excluidos o ya pagado.
    - conciliado False: si estaba PAGADO/PAGO_ADELANTADO, bajar a PENDIENTE (evita PAGADO sin conciliar).
    """
    est_u = str(getattr(row, "estado", "") or "").strip().upper()
    if conciliado_nuevo:
        if est_u in ("PAGADO", "PAGO_ADELANTADO"):
            return
        if est_u in ("DUPLICADO", "ANULADO_IMPORT", "CANCELADO", "RECHAZADO", "REVERSADO"):
            return
        if "ANUL" in est_u or "REVERS" in est_u:
            return
        row.estado = "PAGADO"
        return
    if est_u in ("PAGADO", "PAGO_ADELANTADO"):
        row.estado = "PENDIENTE"


def _estado_conciliacion_post_cascada(pago: Pago, cuotas_completadas: int, cuotas_parciales: int) -> str:
    estado = _estado_pago_tras_aplicar_cascada(cuotas_completadas, cuotas_parciales)

    if estado == "PAGADO":
        return estado

    # ABONOS y demás autoconciliados: mantener conciliado + PAGADO aunque no haya cuota_pagos.
    if pago_preserva_autoconciliacion_sin_cuotas(pago):
        marcar_pago_autoconciliado(pago)
        return "PAGADO"

    # Sin aplicación real: no dejar conciliado=True con PENDIENTE (CHECK en BD).
    if bool(getattr(pago, "conciliado", False)):
        pago.conciliado = False
        pago.fecha_conciliacion = None
        # verificado_concordancia se mantiene (p. ej. SI) para no bloquear «Aplicar a cuotas» masivo.

    return estado


def _alinear_estado_tras_quitar_numero_documento_ocr(row: Pago) -> bool:
    """
    Re-escaneo OCR sin numero_documento real: cumplir chk_pagos_numero_documento_obligatorio_activo
    (pagos activos exigen comprobante en BD; se usa marcador REOCR-PEND-{id}).
    """
    if not sin_documento_real_tras_reocr(row.numero_documento):
        return False
    est_u = str(getattr(row, "estado", "") or "").strip().upper()
    if est_u in ("DUPLICADO", "ANULADO_IMPORT", "CANCELADO", "RECHAZADO", "REVERSADO"):
        return False
    if "ANUL" in est_u or "REVERS" in est_u:
        return False
    cambio = False
    if est_u in ("PAGADO", "PAGO_ADELANTADO"):
        row.estado = "PENDIENTE"
        cambio = True
    if bool(row.conciliado):
        row.conciliado = False
        row.fecha_conciliacion = None
        if str(row.verificado_concordancia or "").strip().upper() == "SI":
            row.verificado_concordancia = "NO"
        cambio = True
    return cambio
