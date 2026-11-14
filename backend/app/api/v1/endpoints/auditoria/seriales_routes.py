"""
Auditoría → Seriales (Pagos): subir Excel y marcar SI/NO si el serial está en BD.
"""
from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.schemas.auth import UserResponse
from app.services.auditoria_seriales_excel_service import (
    exportar_excel_con_si_no,
    verificar_seriales_excel,
)

router = APIRouter(
    prefix="/seriales",
    tags=["auditoria-seriales"],
)


class SerialesItem(BaseModel):
    fila: int
    serial_archivo: str
    serial_norm: Optional[str] = None
    resultado: str = Field(..., description="'si' si está en BD; 'no' si no.")
    en_bd: bool


class SerialesResponse(BaseModel):
    total_filas: int
    encontrados_si: int
    no_encontrados_no: int
    seriales_vacios: int
    items: List[SerialesItem]


def _leer_excel_o_400(file: UploadFile, content: bytes) -> None:
    name = (file.filename or "").lower()
    if not (name.endswith(".xlsx") or name.endswith(".xls")):
        raise HTTPException(
            status_code=400,
            detail="Sube un archivo Excel (.xlsx o .xls).",
        )
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")


@router.post("/verificar", response_model=SerialesResponse)
async def verificar_seriales(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
) -> Any:
    """
    Excel: columna B = Referencia/serial.
    Compara contra pagos.numero_documento y pagos.referencia_pago (cualquier estado).
    Devuelve si/no por fila.
    """
    content = await file.read()
    _leer_excel_o_400(file, content)
    return verificar_seriales_excel(db, content)


@router.post("/verificar/exportar-excel")
async def verificar_y_exportar_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
) -> Response:
    """Misma verificación; descarga el Excel con columna D (SI/NO) en si/no."""
    content = await file.read()
    _leer_excel_o_400(file, content)
    payload = verificar_seriales_excel(db, content)
    data = exportar_excel_con_si_no(content, payload)
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": 'attachment; filename="Auditoria_Seriales_SI_NO.xlsx"',
            "X-Seriales-Total": str(payload.get("total_filas") or 0),
            "X-Seriales-Si": str(payload.get("encontrados_si") or 0),
            "X-Seriales-No": str(payload.get("no_encontrados_no") or 0),
        },
    )
