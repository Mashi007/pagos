"""Registro pasivo de candidatos Drive eliminados en UI (clientes / préstamos)."""
from __future__ import annotations

from typing import Iterable, Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.drive_candidato_eliminado_pasivo import DriveCandidatoEliminadoPasivo

ORIGEN_CLIENTE = "cliente"
ORIGEN_PRESTAMO = "prestamo"
# Fila de hoja ya convertida en préstamo: el refresh no debe reinsertar esa fila
# (J admite n APROBADO, así que omitir solo por cédula bloquearía créditos nuevos).
ORIGEN_PRESTAMO_FILA = "prestamo_fila"

_ORIGENES_VALIDOS = frozenset({ORIGEN_CLIENTE, ORIGEN_PRESTAMO, ORIGEN_PRESTAMO_FILA})


def clave_fila_sheet(sheet_row_number: int) -> str:
    return f"fila:{int(sheet_row_number)}"


def cedulas_eliminadas_pasivas(db: Session, origen: str) -> Set[str]:
    """Conjunto de cédulas normalizadas omitidas para `origen`."""
    rows = db.execute(
        select(DriveCandidatoEliminadoPasivo.cedula_cmp).where(
            DriveCandidatoEliminadoPasivo.origen == origen
        )
    ).scalars().all()
    return {str(c).strip() for c in (rows or []) if c and str(c).strip()}


def filas_sheet_pasivas(db: Session, origen: str = ORIGEN_PRESTAMO_FILA) -> Set[int]:
    """Filas de hoja CONCILIACIÓN ya consumidas (préstamo creado desde el candidato)."""
    rows = db.execute(
        select(DriveCandidatoEliminadoPasivo.sheet_row_number).where(
            DriveCandidatoEliminadoPasivo.origen == origen,
            DriveCandidatoEliminadoPasivo.sheet_row_number.isnot(None),
        )
    ).scalars().all()
    out: Set[int] = set()
    for n in rows or []:
        try:
            ni = int(n)
        except (TypeError, ValueError):
            continue
        if ni > 0:
            out.add(ni)
    return out


def omitir_fila_prestamo_en_refresh(
    *,
    cedula_cmp: str,
    sheet_row_number: Optional[int],
    pasivos_cedula: Set[str],
    filas_consumidas: Set[int],
) -> bool:
    """
    True si el recálculo no debe reinsertar esta fila de Drive.

    - Eliminar en UI: omite toda la cédula (`pasivos_cedula`).
    - Guardar préstamo: omite solo `sheet_row_number` (`filas_consumidas`), para que
      un jurídico pueda seguir trayendo otras filas de la misma cédula.
    """
    if (cedula_cmp or "").strip() in pasivos_cedula:
        return True
    try:
        sr = int(sheet_row_number) if sheet_row_number is not None else 0
    except (TypeError, ValueError):
        return False
    return bool(sr > 0 and sr in filas_consumidas)


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
    if not cmp_e or origen not in _ORIGENES_VALIDOS:
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


def registrar_fila_sheet_consumida(
    db: Session,
    *,
    sheet_row_number: int,
    usuario_email: Optional[str] = None,
    commit: bool = False,
) -> bool:
    """
    La fila de hoja ya originó un préstamo: el recálculo del snapshot no debe
    volver a ofrecerla (crítico para J, donde cupo/huella no bloquean el alta).
    """
    try:
        n = int(sheet_row_number)
    except (TypeError, ValueError):
        return False
    if n <= 0:
        return False
    return registrar_eliminado_pasivo(
        db,
        origen=ORIGEN_PRESTAMO_FILA,
        cedula_cmp=clave_fila_sheet(n),
        sheet_row_number=n,
        usuario_email=usuario_email,
        commit=commit,
    )
