"""Registro pasivo de candidatos Drive eliminados en UI (clientes / préstamos)."""
from __future__ import annotations

from typing import Iterable, Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.drive_candidato_eliminado_pasivo import DriveCandidatoEliminadoPasivo

ORIGEN_CLIENTE = "cliente"
ORIGEN_PRESTAMO = "prestamo"


def cedulas_eliminadas_pasivas(db: Session, origen: str) -> Set[str]:
    """
    Conjunto de cédulas normalizadas omitidas para `origen` (TODAS sus filas).

    OJO: no usar para `ORIGEN_PRESTAMO` si la cédula puede ser tipo J (varias
    filas/preéstamos legítimos): bloquearía TODAS las filas de esa cédula al
    eliminar solo una. Preferir `filas_eliminadas_pasivas` (por fila exacta).
    Se mantiene por compatibilidad con `ORIGEN_CLIENTE` (una sola fila útil).
    """
    rows = db.execute(
        select(DriveCandidatoEliminadoPasivo.cedula_cmp).where(
            DriveCandidatoEliminadoPasivo.origen == origen
        )
    ).scalars().all()
    return {str(c).strip() for c in (rows or []) if c and str(c).strip()}


def filas_eliminadas_pasivas(
    db: Session, origen: str
) -> tuple[Set[tuple[str, int]], Set[str]]:
    """
    Exclusión por FILA exacta (cedula_cmp, sheet_row_number), más un set
    aparte de cédulas cuyo registro pasivo no tiene sheet_row_number
    (datos legacy sin fila): esas sí se excluyen por cédula completa,
    igual que antes, para no perder el bloqueo original.

    Uso recomendado para `ORIGEN_PRESTAMO`: permite que una cédula tipo J
    con varios préstamos legítimos solo pierda la fila eliminada, no todas.
    """
    rows = db.execute(
        select(
            DriveCandidatoEliminadoPasivo.cedula_cmp,
            DriveCandidatoEliminadoPasivo.sheet_row_number,
        ).where(DriveCandidatoEliminadoPasivo.origen == origen)
    ).all()
    filas: Set[tuple[str, int]] = set()
    cedulas_sin_fila: Set[str] = set()
    for cmp_e, sheet_row in rows or []:
        c = str(cmp_e or "").strip()
        if not c:
            continue
        if sheet_row is None:
            cedulas_sin_fila.add(c)
        else:
            filas.add((c, int(sheet_row)))
    return filas, cedulas_sin_fila


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
