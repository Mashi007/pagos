"""Préstamos por cédula del cliente titular (alineado con portal y cupo Drive)."""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    texto_cedula_comparable_bd,
)

# Carga masiva staff / batch pagos (front Excel).
ESTADOS_CREDITO_ACTIVO_CARGA_STAFF: tuple[str, ...] = ("APROBADO", "DESEMBOLSADO")

# Portal cobros, Gmail auto, mover a cartera.
ESTADOS_CREDITO_ACTIVO_PORTAL: tuple[str, ...] = ("APROBADO",)


def cedula_lookup_norm(raw: Optional[str]) -> str:
    return texto_cedula_comparable_bd((raw or "").strip())


def _estado_norm():
    return func.upper(func.trim(func.coalesce(Prestamo.estado, "")))


def select_prestamo_ids_por_cedula_titular(
    db: Session,
    cedula_raw: str,
    *,
    estados: Sequence[str] = ESTADOS_CREDITO_ACTIVO_PORTAL,
    order_desc: bool = False,
) -> list[int]:
    """
    IDs de préstamos cuyo **cliente titular** coincide con la cédula (normalizada).
    No incluye filas que solo coinciden en ``prestamos.cedula`` con otro ``cliente_id``.
    """
    key = cedula_lookup_norm(cedula_raw)
    if not key:
        return []
    estados_u = tuple((e or "").strip().upper() for e in estados if (e or "").strip())
    stmt = (
        select(Prestamo.id)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == key)
    )
    if estados_u:
        stmt = stmt.where(_estado_norm().in_(estados_u))
    stmt = stmt.order_by(Prestamo.id.desc() if order_desc else Prestamo.id.asc())
    return [int(r) for r in db.execute(stmt).scalars().all() if r is not None]


def select_unico_prestamo_id_o_error(
    db: Session,
    cedula_raw: str,
    *,
    estados: Sequence[str] = ESTADOS_CREDITO_ACTIVO_PORTAL,
    contexto: str = "cédula",
) -> tuple[Optional[int], Optional[str]]:
    """Si hay exactamente 1 préstamo en ``estados``, devuelve su id; si no, mensaje de error."""
    ids = select_prestamo_ids_por_cedula_titular(db, cedula_raw, estados=estados)
    ced_disp = (cedula_raw or "").strip() or contexto
    if len(ids) == 1:
        return ids[0], None
    if len(ids) > 1:
        return None, (
            f"{contexto} {ced_disp} con {len(ids)} préstamos en cartera "
            f"({', '.join(estados)}): indique el ID del préstamo."
        )
    return None, (
        f"{contexto} {ced_disp} sin préstamo activo "
        f"({', '.join(estados) if estados else 'ningún estado'})."
    )


def prestamo_ids_activos_por_cedulas_batch(
    db: Session,
    cedulas_raw: Iterable[str],
    *,
    estados: Sequence[str] = ESTADOS_CREDITO_ACTIVO_CARGA_STAFF,
) -> dict[str, list[int]]:
    """
    Mapa cedula_lookup_norm -> [prestamo_id, ...] para batch de pagos.
    Claves = mismas que ``cedula_lookup_norm`` de cada cédula enviada.
    """
    keys = list(dict.fromkeys(cedula_lookup_norm(c) for c in cedulas_raw if (c or "").strip()))
    keys = [k for k in keys if k]
    if not keys:
        return {}
    estados_u = tuple((e or "").strip().upper() for e in estados if (e or "").strip())
    ced_cli = expr_cedula_normalizada_para_comparar(Cliente.cedula)
    stmt = (
        select(Prestamo.id, ced_cli)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(ced_cli.in_(keys))
    )
    if estados_u:
        stmt = stmt.where(_estado_norm().in_(estados_u))
    out: dict[str, list[int]] = {k: [] for k in keys}
    for pid, ccell in db.execute(stmt).all():
        if pid is None:
            continue
        ck = cedula_lookup_norm(str(ccell) if ccell is not None else "")
        if ck and ck in out:
            out[ck].append(int(pid))
    for k in out:
        out[k] = sorted(set(out[k]))
    return out
