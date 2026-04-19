"""
Altas de clientes desde snapshot Drive (pestaña CONCILIACIÓN, columnas D–G).

Solo administradores. Los datos base provienen de la tabla `drive` (sync existente).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.schemas.auth import UserResponse
from app.services.cliente_alta_desde_drive_service import (
    importar_seleccion_desde_drive,
    listar_auditoria,
    obtener_candidatos_drive_para_api,
    refrescar_cache_candidatos_drive,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/candidatos", summary="Cédulas en Drive no registradas en clientes (admin)")
def get_drive_clientes_candidatos(
    fresh: bool = Query(
        False,
        description="Si true, ignora la caché materializada y recalcula al vuelo (luego persiste caché).",
    ),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
):
    return obtener_candidatos_drive_para_api(db, forzar_calculo=bool(fresh))


@router.post("/refresh-cache", summary="Recalcular y persistir lista candidatos Drive (admin)")
def post_drive_clientes_refresh_cache(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
):
    """Útil manualmente; el job dom/mié 03:00 Caracas hace lo mismo tras el sync de la hoja."""
    return refrescar_cache_candidatos_drive(db)


class ImportarClientesDriveBody(BaseModel):
    sheet_row_numbers: List[int] = Field(default_factory=list)
    comentario: Optional[str] = None


@router.post("/importar", summary="Insertar clientes seleccionados (mismas reglas que POST /clientes)")
def post_drive_clientes_importar(
    body: ImportarClientesDriveBody,
    db: Session = Depends(get_db),
    current: UserResponse = Depends(require_admin),
):
    email = (current.email or "").strip() or "admin@sistema"
    return importar_seleccion_desde_drive(
        db,
        usuario_email=email,
        comentario=(body.comentario or "").strip() or None,
        sheet_rows=body.sheet_row_numbers or [],
    )


@router.get("/auditoria", summary="Historial de importaciones desde Drive")
def get_drive_clientes_auditoria(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
):
    return listar_auditoria(db, page=page, per_page=per_page)
