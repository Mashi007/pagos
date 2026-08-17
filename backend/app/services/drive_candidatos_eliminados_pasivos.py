"""Registro pasivo de candidatos Drive eliminados en UI (clientes / préstamos)."""
from __future__ import annotations

from typing import Iterable, Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.drive_candidato_eliminado_pasivo import DriveCandidatoEliminadoPasivo

ORIGEN_CLIENTE = "cliente"
ORIGEN_PRESTAMO = "prestamo"


def cedulas_eliminadas_pasivas(db: Session, origen: str) -> Set[str]:
    """Conjunto de cédulas normalizadas omitidas para `origen`."""
    rows = db.execute(
        select(DriveCandidatoEliminadoPasivo.cedula_cmp).where(
            DriveCandidatoEliminadoPasivo.origen == origen
        )
    ).scalars().all()
    return {str(c).strip() for c in (rows or []) if c and str(c).strip()}


def registrar_eliminado_pasivo(
    db: Session,
    *,
    origen: str,
    cedula_cmp: str,
    sheet_row_number: Optional[int] = None,
    usuario_email: Optional[str] = None,
    commit: bool = False,
) -> bool:
    """
    Marca una cédula como eliminada pasiva para no volver a listarla.
    Si ya existe, actualiza fila/usuario. Devuelve True si hubo alta o update.
    """
    cmp_e = (cedula_cmp or "").strip()
    if not cmp_e or origen not in (ORIGEN_CLIENTE, ORIGEN_PRESTAMO):
        return False
    existing = db.execute(
        select(DriveCandidatoEliminadoPasivo).where(
            DriveCandidatoEliminadoPasivo.origen == origen,
            DriveCandidatoEliminadoPasivo.cedula_cmp == cmp_e[:32],
        )
    ).scalar_one_or_none()
    email = (usuario_email or "").strip() or None
    if existing is None:
        db.add(
            DriveCandidatoEliminadoPasivo(
                origen=origen,
                cedula_cmp=cmp_e[:32],
                sheet_row_number=int(sheet_row_number) if sheet_row_number else None,
                usuario_email=email,
            )
        )
    else:
        if sheet_row_number:
            existing.sheet_row_number = int(sheet_row_number)
        if email:
            existing.usuario_email = email
    if commit:
        db.commit()
    else:
        db.flush()
    return True


def registrar_eliminados_pasivos_bulk(
    db: Session,
    *,
    origen: str,
    items: Iterable[tuple[str, Optional[int]]],
    usuario_email: Optional[str] = None,
) -> int:
    """Registra varios (cedula_cmp, sheet_row_number). Devuelve cuántos se procesaron."""
    n = 0
    for ced, sheet_row in items:
        if registrar_eliminado_pasivo(
            db,
            origen=origen,
            cedula_cmp=ced,
            sheet_row_number=sheet_row,
            usuario_email=usuario_email,
            commit=False,
        ):
            n += 1
    return n
