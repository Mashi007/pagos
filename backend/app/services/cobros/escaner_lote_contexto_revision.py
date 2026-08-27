# -*- coding: utf-8 -*-
"""Precarga de comprobantes para escáner lote (cartera vs pagos_con_errores)."""
from __future__ import annotations

from typing import Any, Optional, Type

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pago import Pago
from app.models.pago_con_error import PagoConError

ORIGEN_PAGOS = "pagos"
ORIGEN_PAGOS_CON_ERRORES = "pagos_con_errores"

_ORIGENES_PAGO_CON_ERROR = frozenset(
    {
        "pagos-con-errores",
        "pago-con-error",
        "revision-errores",
    }
)


def origen_es_pago_con_error(origen: Optional[str]) -> bool:
    raw = (origen or "").strip().lower().replace("_", "-")
    return raw in _ORIGENES_PAGO_CON_ERROR


def modelo_contexto_revision(origen: Optional[str]) -> Type[Any]:
    """Tabla de la que salen los IDs de ``/escaner/lote/contexto-revision``."""
    if origen_es_pago_con_error(origen):
        return PagoConError
    return Pago


def tabla_contexto_revision(origen: Optional[str]) -> str:
    if origen_es_pago_con_error(origen):
        return ORIGEN_PAGOS_CON_ERRORES
    return ORIGEN_PAGOS


def parse_ids_contexto_revision(ids_raw: Optional[str], *, max_ids: int = 10) -> list[int]:
    out: list[int] = []
    for x in (ids_raw or "").split(","):
        s = x.strip()
        if not s:
            continue
        try:
            n = int(s)
        except (TypeError, ValueError):
            continue
        if n > 0:
            out.append(n)
        if len(out) >= max_ids:
            break
    return out


def cargar_filas_contexto_revision(
    db: Session,
    ids: list[int],
    *,
    origen: Optional[str] = None,
) -> tuple[str, dict[int, Any]]:
    """
    Carga filas por ID de la tabla indicada por ``origen``.

    Pagos → Revisión (pagos_con_errores) y cartera (pagos) son PKs independientes;
    no se hace fallback entre tablas (un id 8842 en ambas no debe cruzarse).
    """
    tabla = tabla_contexto_revision(origen)
    model = modelo_contexto_revision(origen)
    if not ids:
        return tabla, {}
    rows = db.execute(select(model).where(model.id.in_(ids))).scalars().all()
    by_id = {int(r.id): r for r in rows if r is not None}
    return tabla, by_id
