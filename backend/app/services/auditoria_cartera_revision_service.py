"""Consultas y validacion para auditoria_cartera_revision."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

# Codigos emitidos por prestamo_cartera_auditoria.add_control (deben alinearse con el catalogo frontend).
CONTROLES_CARTERA_VALIDOS = frozenset(
    {
        "cedula_cliente_vs_prestamo",
        "prestamos_duplicados_misma_cedula",
        "prestamos_duplicados_nombre_cedula_fecha_registro",
        "pagos_mismo_dia_monto",
        "pagos_monto_no_positivo",
        "total_pagado_vs_aplicado_cuotas",
        "total_financiamiento_vs_suma_cuotas",
        "sin_cuotas",
        "numero_cuotas_inconsistente",
        "liquidado_con_cuota_pendiente",
        "estado_cuota_vs_calculo",
        "pago_bs_sin_tasa_cambio_diaria",
        "conversion_bs_a_usd_incoherente",
        "pagos_sin_aplicacion_a_cuotas",
    }
)

TIPOS_REVISION_VALIDOS = frozenset({"MARCAR_OK"})


def parches_ocultos_por_ultima_revision(
    db: Session,
    prestamo_ids: list[int],
) -> list[dict[str, Any]]:
    """
    Por cada (prestamo_id, codigo_control) devuelve el ultimo `tipo` por creado_en.
    La UI oculta el control si tipo == MARCAR_OK.
    """
    if not prestamo_ids:
        return []
    q = text(
        """
        SELECT DISTINCT ON (r.prestamo_id, r.codigo_control)
          r.prestamo_id,
          r.codigo_control,
          r.tipo
        FROM auditoria_cartera_revision r
        WHERE r.prestamo_id = ANY(:ids)
        ORDER BY r.prestamo_id, r.codigo_control, r.creado_en DESC
        """
    )
    rows = db.execute(q, {"ids": list({int(x) for x in prestamo_ids if x})}).fetchall()
    return [
        {
            "prestamo_id": int(r[0]),
            "codigo_control": str(r[1]),
            "tipo": str(r[2] or ""),
        }
        for r in rows
    ]


def listar_ocultos_marcar_ok(db: Session, prestamo_ids: list[int]) -> list[dict[str, int | str]]:
    """Pares (prestamo_id, codigo_control) cuyo ultimo evento es MARCAR_OK."""
    out: list[dict[str, int | str]] = []
    for row in parches_ocultos_por_ultima_revision(db, prestamo_ids):
        if (row.get("tipo") or "").upper() == "MARCAR_OK":
            out.append(
                {
                    "prestamo_id": int(row["prestamo_id"]),
                    "codigo_control": str(row["codigo_control"]),
                }
            )
    return out


def iso_utc(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")
