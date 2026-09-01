# -*- coding: utf-8 -*-
"""API Importación extracto (faltantes) — Auditoría (admin)."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.schemas.auth import UserResponse
from app.services import importacion_extracto_service as svc

router = APIRouter(
    prefix="/importacion-extracto",
    tags=["importacion-extracto"],
    dependencies=[Depends(require_admin)],
)


class IdsBody(BaseModel):
    fila_ids: List[int] = Field(..., min_length=1)


@router.post("/lotes")
async def subir_excel(
    archivo: UploadFile = File(...),
    banco: str = Form(...),
    modo_cedula: bool = Form(True),
    modo_serial: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    return svc.crear_lote_desde_excel(
        db,
        archivo,
        usuario_id=getattr(current_user, "id", None),
        banco=banco,
        modo_cedula=modo_cedula,
        modo_serial=modo_serial,
    )


@router.get("/lotes")
def listar_lotes(
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    return {"lotes": svc.listar_lotes(db)}


@router.get("/lotes/{lote_id}/filas")
def listar_filas(
    lote_id: int,
    estado: Optional[str] = None,
    solo_importables: bool = False,
    solo_ocultos: bool = False,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    return {
        "lote_id": lote_id,
        "filas": svc.listar_filas(
            db,
            lote_id,
            estado=estado,
            solo_importables=solo_importables,
            solo_ocultos=solo_ocultos,
        ),
    }


@router.post("/filas/visto")
def marcar_visto(
    body: IdsBody,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    return svc.marcar_visto(db, body.fila_ids)


@router.post("/filas/ocultar")
def ocultar_filas(
    body: IdsBody,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    """Oculta casos del listado (auditoría); no elimina el registro del lote."""
    return svc.ocultar_filas(db, body.fila_ids)


@router.post("/filas/importar")
def importar(
    body: IdsBody,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    """OK individual o lote: autoriza importación de filas SE_PUEDE_IMPORTAR."""
    return svc.importar_filas(db, body.fila_ids)
