"""Endpoints Conciliacion Bancos (solo admin)."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

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
    pago_id_elegido: Optional[int] = Field(
        None,
        description="Obligatorio en AMBIGUO+CORREGIR: pago/prestamo elegido entre candidatos",
    )


class CompararBody(BaseModel):
    bancos: List[str] = Field(
        default_factory=list,
        description="Categorias: Mercantil, BNC, Binance, BNV, Recibos, Drive, Otros",
    )
    fecha_desde: Optional[date] = Field(
        None, description="Opcional: actualiza rango BD del lote antes de comparar"
    )
    fecha_hasta: Optional[date] = Field(
        None, description="Opcional: actualiza rango BD del lote antes de comparar"
    )


class DecisionMasivaItem(BaseModel):
    resultado_id: int
    fuente_elegida: Optional[str] = None
    pago_id_elegido: Optional[int] = None


class DecisionMasivaBody(BaseModel):
    items: List[DecisionMasivaItem]
    fuente_default: str = Field(
        default="BANCO", description="BD | BANCO si el item no trae fuente"
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
        "bancos_filtro": svc._leer_bancos_de_lote(lote),
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
    body: CompararBody = CompararBody(),
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    return {
        "ok": True,
        **svc.comparar_lote(
            db,
            lote_id,
            bancos_filtro=body.bancos,
            fecha_desde=body.fecha_desde,
            fecha_hasta=body.fecha_hasta,
        ),
    }


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
        pago_id_elegido=body.pago_id_elegido,
    )


@router.post("/resultados/decidir-masivo")
def decidir_masivo(
    body: DecisionMasivaBody,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(require_admin),
):
    return svc.decidir_masivo(
        db,
        [i.model_dump() for i in body.items],
        usuario_id=getattr(user, "id", None),
        fuente_default=body.fuente_default,
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