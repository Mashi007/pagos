"""Alineación de estado de pago con flags de conciliación y post-cascada."""

from app.models.pago import Pago

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

    # Si no hubo aplicacion real, el pago no puede quedar conciliado en estado PENDIENTE.
    if estado == "PENDIENTE" and bool(getattr(pago, "conciliado", False)):
        pago.conciliado = False
        pago.fecha_conciliacion = None
        # verificado_concordancia se mantiene (p. ej. SI) para no bloquear «Aplicar a cuotas» masivo.

    return estado
