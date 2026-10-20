"""Alineación de estado de pago con flags de conciliación y post-cascada."""

from app.models.pago import Pago
from app.services.pago_autoconciliacion import marcar_pago_autoconciliado
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


def _estado_conciliacion_post_cascada(
    pago: Pago,
    cuotas_completadas: int,
    cuotas_parciales: int,
    db=None,
) -> str:
    """
    Alinea estado tras cascada.

    Política base: autoconciliar (conciliado + SI + PAGADO) aunque la cascada no
    genere cuota_pagos (remanente / cupo cubierto / ABONOS).

    Anti-limbo: si se pasa ``db`` y el pago quedaria PAGADO sin cuota_pagos con
    cupo aun pendiente en cuotas, se demota a PENDIENTE (mismo criterio que
    portal Infopagos / Excel). Callers sin ``db`` conservan el comportamiento previo.
    """
    _ = (cuotas_completadas, cuotas_parciales, _estado_pago_tras_aplicar_cascada)
    marcar_pago_autoconciliado(pago)
    if db is not None and getattr(pago, "id", None) is not None:
        from app.services.cuota_pago_integridad import (
            demotar_pago_sin_aplicacion,
            pago_quedaria_limbo_pagado_sin_cuotas,
        )

        if pago_quedaria_limbo_pagado_sin_cuotas(db, pago):
            demotar_pago_sin_aplicacion(pago)
            return "PENDIENTE"
    return "PAGADO"


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
