"""
Snapshot de candidatos a préstamo nuevo desde tabla `drive` (CONCILIACIÓN).

Solo administradores. El refresco automático corre domingo y miércoles ~04:05 (tras sync 04:00).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.schemas.auth import UserResponse
from app.services.prestamo_candidatos_drive_job import (
    ejecutar_refresh_prestamo_candidatos_drive,
    listar_prestamo_candidatos_drive_snapshot,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/snapshot", summary="Listar último snapshot de candidatos préstamo (Drive)")
def get_prestamos_candidatos_drive_snapshot(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
):
    return listar_prestamo_candidatos_drive_snapshot(db)


@router.post("/refrescar", summary="Recalcular snapshot ahora (misma lógica que el cron)")
def post_prestamos_candidatos_drive_refrescar(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
):
    return ejecutar_refresh_prestamo_candidatos_drive(db)
