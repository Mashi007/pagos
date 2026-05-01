"""Mensajes de diagnóstico para cascada por préstamo (sin dependencia de FastAPI)."""

from __future__ import annotations

from typing import Any


def _mensaje_sin_aplicacion_cascada(diagnostico: dict[str, Any]) -> str:
    """Texto explicativo cuando pagos_con_aplicacion == 0 sin reaplicación completa."""
    n_no = int(diagnostico.get("pagos_no_elegibles_sin_cuota_pagos") or 0)
    n_eleg = int(diagnostico.get("pagos_elegibles_cascada_sin_cuota_pagos") or 0)
    n_oper = int(diagnostico.get("pagos_operativos_sin_cuota_pagos") or 0)
    sin_abono = diagnostico.get("pagos_con_intento_sin_abono_ids") or []
    errs = diagnostico.get("errores_por_pago") or []
    partes: list[str] = []
    if n_no > 0 and n_eleg == 0:
        partes.append(
            f"Hay {n_no} pago(s) sin articulación en cuota_pagos que no cumplen criterio de elegibilidad "
            "(conciliado, verificado SÍ o estado PAGADO; excluye anulados/rechazados). "
            "Concilie o verifique esos pagos en el módulo Pagos."
        )
    elif n_eleg > 0 and isinstance(sin_abono, list) and len(sin_abono) > 0:
        muestra = ", ".join(str(x) for x in sin_abono[:20])
        suf = "…" if len(sin_abono) > 20 else ""
        partes.append(
            f"Se intentó con {n_eleg} pago(s) elegible(s) ordenados por fecha, "
            f"pero ninguno generó abono en cuotas (sin saldo pendiente en cuotas en BD o bloqueo). "
            f"IDs: {muestra}{suf}."
        )
    elif n_oper == 0:
        partes.append(
            "No hay pagos operativos con monto > 0 pendientes de articulación para este crédito "
            "(todos tienen al menos una fila en cuota_pagos a nivel global, o no hay registros aplicables). "
            "Eso no implica que el dinero esté bien repartido en las cuotas de este préstamo: "
            "si el sistema detecta desajuste entre pagos elegibles y monto articulado a sus cuotas, "
            "reconstruye la cascada automáticamente al pulsar de nuevo."
        )
    if isinstance(errs, list) and len(errs) > 0:
        partes.append(f"Fallos al aplicar en {len(errs)} pago(s); revise logs o integridad.")
    if not partes:
        partes.append(
            "No quedaban pagos elegibles sin filas en cuota_pagos (o monto 0). "
            "La reaplicación completa corre si hay inconsistencia de integridad en cuotas "
            "o si el monto elegible en pagos supera lo articulado a las cuotas de este préstamo."
        )
    return "Ningún pago nuevo se articuló en cuotas. " + " ".join(partes)
