"""
Auditoría → Conciliacion_finiquitos: subir Excel de cédulas y ver estado en sistema.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.schemas.auth import UserResponse
from app.services.auditoria_conciliacion_finiquitos_service import (
    comparar_cedulas_archivo_vs_sistema,
    exportar_resultado_excel,
)

router = APIRouter(
    prefix="/conciliacion-finiquitos",
    tags=["auditoria-conciliacion-finiquitos"],
)


class ConciliacionFiniquitosItem(BaseModel):
    cedula_archivo: str
    en_sistema: bool
    cliente_id: Optional[int] = None
    nombres: Optional[str] = None
    prestamo_id: Optional[int] = None
    estado_prestamo: Optional[str] = None
    estado_gestion_finiquito: Optional[str] = None
    caso_finiquito_id: Optional[int] = None
    estado_caso_finiquito: Optional[str] = None
    estado_sistema: str = Field(
        ...,
        description="Estado del préstamo en BD, o NO_ENCONTRADA si la cédula no está en sistema.",
    )


class ConciliacionFiniquitosResponse(BaseModel):
    total_cedulas_archivo: int
    total_filas_resultado: int
    encontradas: int
    no_encontradas: int
    por_estado_sistema: Dict[str, int]
    items: List[ConciliacionFiniquitosItem]


@router.post("/comparar", response_model=ConciliacionFiniquitosResponse)
async def comparar_excel_finiquitos(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
) -> Any:
    """
    Excel con cédulas en columna A (archivo de finiquitos).
    Devuelve cada cédula con el estado real del préstamo en el sistema.
    """
    name = (file.filename or "").lower()
    if not (name.endswith(".xlsx") or name.endswith(".xls")):
        raise HTTPException(
            status_code=400,
            detail="Sube un archivo Excel (.xlsx o .xls).",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    return comparar_cedulas_archivo_vs_sistema(db, content)


@router.post("/comparar/exportar-excel")
async def comparar_y_exportar_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
) -> Response:
    """Misma comparación y descarga del resultado en Excel."""
    name = (file.filename or "").lower()
    if not (name.endswith(".xlsx") or name.endswith(".xls")):
        raise HTTPException(
            status_code=400,
            detail="Sube un archivo Excel (.xlsx o .xls).",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    payload = comparar_cedulas_archivo_vs_sistema(db, content)
    data = exportar_resultado_excel(payload)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="Conciliacion_finiquitos.xlsx"'
        },
    )
