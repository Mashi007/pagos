"""Endpoints Conciliacion Bancos (solo admin)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.conciliacion_banco_ocr import ConciliacionBancoOcrLote
from app.schemas.auth import UserResponse
from app.services import conciliacion_bancos_service as svc

router = APIRouter(
    prefix="/conciliacion-bancos",
    tags=["conciliacion-bancos"],
    dependencies=[Depends(require_admin)],
)


class DecisionBody(BaseModel):
    decision: str = Field(..., description="VISTO | CORREGIR | OMITIR")
    fuente_elegida: Optional[str] = Field(
        None, description="BD | BANCO (requerido si decision=CORREGIR)"
    )


def _lote_dict(lote: ConciliacionBancoOcrLote) -> dict:
    return {
        "id": lote.id,
        "archivo_nombre": lote.archivo_nombre,
        "fecha_desde": lote.fecha_desde.isoformat() if lote.fecha_desde else None,
        "fecha_hasta": lote.fecha_hasta.isoformat() if lote.fecha_hasta else None,
        "estado": lote.estado,
        "moneda_carga": lote.moneda_carga,
        "usuario_id": lote.usuario_id,
        "creado_en": lote.creado_en.isoformat() if lote.creado_en else None,
    }


@router.post("/lotes")
async def crear_lote(
    file: UploadFile = File(...),
    moneda_carga: str = Form("USD"),
    fecha_desde: date = Form(...),
    fecha_hasta: date = Form(...),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(require_admin),
):
    content = await file.read()
    lote = svc.crear_lote_desde_excel(
        db,
        file=file,
        content=content,
        moneda_carga=moneda_carga,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        usuario_id=getattr(user, "id", None),
    )
    return {"ok": True, "lote": _lote_dict(lote)}


@router.get("/lotes/{lote_id}")
def obtener_lote(
    lote_id: int,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    lote = db.get(ConciliacionBancoOcrLote, lote_id)
    if not lote:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return {"ok": True, "lote": _lote_dict(lote)}


@router.post("/lotes/{lote_id}/comparar")
def comparar(
    lote_id: int,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    return {"ok": True, **svc.comparar_lote(db, lote_id)}


@router.get("/lotes/{lote_id}/resultados")
def resultados(
    lote_id: int,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    return {"ok": True, "items": svc.listar_resultados(db, lote_id)}


@router.post("/resultados/{resultado_id}/decidir")
def decidir(
    resultado_id: int,
    body: DecisionBody,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(require_admin),
):
    return svc.decidir_y_aplicar(
        db,
        resultado_id,
        decision=body.decision,
        fuente_elegida=body.fuente_elegida,
        usuario_id=getattr(user, "id", None),
    )


@router.get("/lotes/{lote_id}/exportar-excel")
def exportar(
    lote_id: int,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    data = svc.exportar_excel_lote(db, lote_id)
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="conciliacion_bancos_lote_{lote_id}.xlsx"'
        },
    )