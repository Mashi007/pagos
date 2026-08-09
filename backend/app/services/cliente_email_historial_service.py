# -*- coding: utf-8 -*-
"""
Historial de correos de clientes: archivar al cambiar y consultar por cliente/cedula.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, Optional, Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cliente_email_historial import ClienteEmailHistorial

logger = logging.getLogger(__name__)


def _norm_email(raw: Optional[str]) -> str:
    return (raw or "").strip().lower()


def _display_email(raw: Optional[str]) -> str:
    return (raw or "").strip()


def archivar_email_si_cambio(
    db: Session,
    *,
    cliente_id: int,
    cedula: str,
    email_anterior: Optional[str],
    email_nuevo: Optional[str],
    rol: str,
    usuario_cambio: Optional[str] = None,
) -> bool:
    """
    Si el correo anterior es distinto del nuevo y no esta vacio, lo guarda en historial.
    Idempotente por (cliente_id, email_norm): no duplica la misma direccion.
    Retorna True si se intento archivar (insert o upsert).
    """
    ant = _display_email(email_anterior)
    nuevo = _display_email(email_nuevo)
    ant_n = _norm_email(ant)
    nuevo_n = _norm_email(nuevo)
    if not ant_n or "@" not in ant:
        return False
    if ant_n == nuevo_n:
        return False

    ahora = datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)
    rol_safe = (rol or "principal").strip().lower()
    if rol_safe not in ("principal", "secundario"):
        rol_safe = "principal"

    stmt = (
        pg_insert(ClienteEmailHistorial)
        .values(
            cliente_id=cliente_id,
            cedula=(cedula or "").strip() or "Z999999999",
            email=ant[:150],
            email_norm=ant_n[:150],
            rol=rol_safe,
            registrado_en=ahora,
            usuario_cambio=(usuario_cambio or None),
        )
        .on_conflict_do_update(
            constraint="uq_cliente_emails_historial_cliente_email",
            set_={
                "cedula": (cedula or "").strip() or "Z999999999",
                "email": ant[:150],
                "rol": rol_safe,
                "registrado_en": ahora,
                "usuario_cambio": (usuario_cambio or None),
            },
        )
    )
    try:
        db.execute(stmt)
        return True
    except Exception as e:
        # Fallback SQLite / BD sin constraint con ese nombre: insert ignore manual.
        logger.warning(
            "cliente_email_historial upsert fallo (%s); intento insert simple",
            e,
        )
        exists = db.execute(
            select(ClienteEmailHistorial.id).where(
                ClienteEmailHistorial.cliente_id == cliente_id,
                ClienteEmailHistorial.email_norm == ant_n,
            )
        ).first()
        if exists:
            row = db.get(ClienteEmailHistorial, exists[0])
            if row:
                row.cedula = (cedula or "").strip() or "Z999999999"
                row.email = ant[:150]
                row.rol = rol_safe
                row.registrado_en = ahora
                row.usuario_cambio = usuario_cambio or None
            return True
        db.add(
            ClienteEmailHistorial(
                cliente_id=cliente_id,
                cedula=(cedula or "").strip() or "Z999999999",
                email=ant[:150],
                email_norm=ant_n[:150],
                rol=rol_safe,
                registrado_en=ahora,
                usuario_cambio=usuario_cambio or None,
            )
        )
        return True


def archivar_cambios_emails_cliente(
    db: Session,
    row: Cliente,
    *,
    email_nuevo: Optional[str],
    email_secundario_nuevo: Optional[str],
    email_en_payload: bool,
    email_secundario_en_payload: bool,
    usuario_cambio: Optional[str] = None,
) -> None:
    """Archiva correo 1 y/o correo 2 si el payload los cambia respecto al valor actual en fila."""
    if not email_en_payload and not email_secundario_en_payload:
        return
    cedula = str(getattr(row, "cedula", "") or "")
    if email_en_payload:
        archivar_email_si_cambio(
            db,
            cliente_id=int(row.id),
            cedula=cedula,
            email_anterior=str(getattr(row, "email", "") or ""),
            email_nuevo=email_nuevo,
            rol="principal",
            usuario_cambio=usuario_cambio,
        )
    if email_secundario_en_payload:
        archivar_email_si_cambio(
            db,
            cliente_id=int(row.id),
            cedula=cedula,
            email_anterior=str(getattr(row, "email_secundario", "") or "") or None,
            email_nuevo=email_secundario_nuevo,
            rol="secundario",
            usuario_cambio=usuario_cambio,
        )


def listar_emails_historial_cliente(
    db: Session,
    cliente_id: int,
    *,
    excluir_vigentes: Optional[Iterable[str]] = None,
) -> list[str]:
    """Correos archivados del cliente (orden: mas reciente primero), sin vigentes si se indican."""
    excl = {_norm_email(x) for x in (excluir_vigentes or []) if _norm_email(x)}
    rows = db.execute(
        select(ClienteEmailHistorial.email, ClienteEmailHistorial.email_norm)
        .where(ClienteEmailHistorial.cliente_id == cliente_id)
        .order_by(ClienteEmailHistorial.registrado_en.desc(), ClienteEmailHistorial.id.desc())
    ).all()
    out: list[str] = []
    seen: set[str] = set()
    for email, email_norm in rows:
        n = (email_norm or _norm_email(email)).strip().lower()
        if not n or n in seen or n in excl:
            continue
        seen.add(n)
        out.append(_display_email(email) or n)
    return out


def map_correos_historial_por_cliente_ids(
    db: Session,
    cliente_ids: Sequence[int],
    vigentes_por_id: Optional[dict[int, Iterable[str]]] = None,
) -> dict[int, list[str]]:
    """Batch: cliente_id -> lista de correos pasados (excluye vigentes del mapa)."""
    if not cliente_ids:
        return {}
    ids = [int(x) for x in cliente_ids]
    rows = db.execute(
        select(
            ClienteEmailHistorial.cliente_id,
            ClienteEmailHistorial.email,
            ClienteEmailHistorial.email_norm,
            ClienteEmailHistorial.registrado_en,
            ClienteEmailHistorial.id,
        )
        .where(ClienteEmailHistorial.cliente_id.in_(ids))
        .order_by(
            ClienteEmailHistorial.cliente_id.asc(),
            ClienteEmailHistorial.registrado_en.desc(),
            ClienteEmailHistorial.id.desc(),
        )
    ).all()
    vigentes_por_id = vigentes_por_id or {}
    out: dict[int, list[str]] = {i: [] for i in ids}
    seen: dict[int, set[str]] = {i: set() for i in ids}
    for cid, email, email_norm, _reg, _hid in rows:
        n = (email_norm or _norm_email(email)).strip().lower()
        if not n:
            continue
        excl = {_norm_email(x) for x in (vigentes_por_id.get(int(cid)) or []) if _norm_email(x)}
        if n in excl or n in seen[int(cid)]:
            continue
        seen[int(cid)].add(n)
        out[int(cid)].append(_display_email(email) or n)
    return out


def cliente_ids_con_email_historial_ilike(db: Session, pattern: str) -> list[int]:
    """IDs de cliente cuyo historial coincide con ILIKE pattern (p. ej. %foo@bar%)."""
    if not (pattern or "").strip():
        return []
    rows = db.execute(
        select(ClienteEmailHistorial.cliente_id)
        .where(
            or_(
                ClienteEmailHistorial.email.ilike(pattern),
                ClienteEmailHistorial.email_norm.ilike(pattern),
            )
        )
        .distinct()
    ).all()
    return [int(r[0]) for r in rows if r and r[0] is not None]


def cedula_por_email_historial(db: Session, email_raw: str) -> Optional[str]:
    """Si el remitente esta solo en historial, devuelve la cedula del cliente."""
    em = _norm_email(email_raw)
    if not em or "@" not in em:
        return None
    row = db.execute(
        select(ClienteEmailHistorial.cedula, Cliente.cedula)
        .select_from(ClienteEmailHistorial)
        .join(Cliente, Cliente.id == ClienteEmailHistorial.cliente_id)
        .where(ClienteEmailHistorial.email_norm == em)
        .order_by(ClienteEmailHistorial.registrado_en.desc())
        .limit(1)
    ).first()
    if not row:
        return None
    return (row[1] or row[0] or "").strip() or None
