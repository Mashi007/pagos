"""
Snapshot de candidatos a préstamo nuevo desde tabla `drive` (CONCILIACIÓN).

Solo administradores. El refresco automático corre domingo y miércoles ~04:05 (tras sync 04:00).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.schemas.auth import UserResponse
from app.services.prestamo_candidatos_drive_guardar import (
    ejecutar_guardar_candidatos_drive_una_fila,
    ejecutar_guardar_candidatos_drive_validados_100,
)
from app.services.prestamo_candidatos_drive_job import (
    ejecutar_refresh_prestamo_candidatos_drive,
    listar_prestamo_candidatos_drive_snapshot,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/snapshot", summary="Listar último snapshot de candidatos préstamo (Drive)")
def get_prestamos_candidatos_drive_snapshot(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
    limit: int = Query(500, ge=1, le=2000, description="Máximo de filas por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    cedula_q: Optional[str] = Query(
        None,
        max_length=64,
        description="Filtro por cédula (substring sobre cédula normalizada en BD)",
    ),
):
    return listar_prestamo_candidatos_drive_snapshot(
        db, limit=limit, offset=offset, cedula_q=cedula_q
    )


@router.post(
    "/guardar-validados-100",
    summary="Crear préstamos solo para candidatos al 100% de validadores (sin selección manual)",
)
def post_prestamos_candidatos_drive_guardar_validados_100(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    return ejecutar_guardar_candidatos_drive_validados_100(db, current_user=current_user)


class PrestamoCandidatoDriveGuardarFilaBody(BaseModel):
    sheet_row_number: int = Field(..., ge=1, le=1_000_000)


@router.post(
    "/guardar-fila",
    summary="Crear préstamo solo para una fila del snapshot si cumple el 100% de validadores",
)
def post_prestamos_candidatos_drive_guardar_fila(
    body: PrestamoCandidatoDriveGuardarFilaBody,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    return ejecutar_guardar_candidatos_drive_una_fila(
        db, current_user=current_user, sheet_row_number=body.sheet_row_number
    )


@router.post("/refrescar", summary="Recalcular snapshot ahora (misma lógica que el cron)")
def post_prestamos_candidatos_drive_refrescar(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
    forzar: bool = Query(
        False,
        description="Si true y la tabla drive está vacía, vacía el snapshot igualmente (solo manual).",
    ),
):
    return ejecutar_refresh_prestamo_candidatos_drive(db, forzar=forzar)
