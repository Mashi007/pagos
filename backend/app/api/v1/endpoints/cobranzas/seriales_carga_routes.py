"""
Cobranzas → Seriales (solo itmaster@): carga pagos Mercantil a préstamos atrasados.
"""
from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_it_master_admin
from app.schemas.auth import UserResponse
from app.services.cobranzas.seriales_carga_service import (
    MAX_DESHACER,
    MAX_GUARDAR_CEDULA,
    MAX_PRESTAMOS_LOTE,
    MESES_REVISION,
    TOLERANCIA_REVISION,
    deshacer_pagos_seriales,
    guardar_revision_cedula,
    procesar_lote_seriales,
    revision_cedula,
)

router = APIRouter(
    prefix="/seriales",
    tags=["cobranzas-seriales"],
    dependencies=[Depends(require_it_master_admin)],
)


class DepositoIn(BaseModel):
    id: int = Field(..., description="Índice de la fila en el Excel de depósitos (cola)")
    fecha: Optional[str] = None
    serial: Optional[str] = None
    monto: Optional[str] = None


class LoteSerialesIn(BaseModel):
    cedulas: List[str] = Field(..., max_length=MAX_PRESTAMOS_LOTE)
    depositos: List[DepositoIn]
    usados: List[int] = Field(default_factory=list)
    simular: bool = False
    tolerancia_pct: float = Field(20, ge=0, le=50)
    max_meses_adelante: int = Field(2, ge=0, le=24)


class RevisionCedulaIn(BaseModel):
    cedula: str
    depositos: List[DepositoIn]
    usados: List[int] = Field(default_factory=list)
    tolerancia_pct: float = Field(TOLERANCIA_REVISION, ge=0, le=50)
    meses_despues: int = Field(MESES_REVISION, ge=1, le=12)


class GuardarCedulaIn(BaseModel):
    cedula: str
    prestamo_id: int
    depositos: List[DepositoIn] = Field(..., min_length=1, max_length=MAX_GUARDAR_CEDULA)


class DeshacerIn(BaseModel):
    pago_ids: List[int] = Field(..., max_length=MAX_DESHACER)


@router.post("/procesar-lote")
def procesar_lote(
    body: LoteSerialesIn,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_it_master_admin),
) -> Any:
    """Procesa hasta 20 cédulas (o las simula sin escribir); devuelve asignaciones."""
    return procesar_lote_seriales(
        db,
        cedulas=list(body.cedulas),
        depositos=[d.model_dump() for d in body.depositos],
        usados=list(body.usados or []),
        simular=body.simular,
        tolerancia_pct=body.tolerancia_pct,
        max_meses_adelante=body.max_meses_adelante,
    )


@router.post("/deshacer")
def deshacer(
    body: DeshacerIn,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(require_it_master_admin),
) -> Any:
    """Elimina pagos creados por este módulo y realinea cuotas (solo usuario de seriales)."""
    return deshacer_pagos_seriales(db, list(body.pago_ids), current_user=user)


@router.post("/revision-cedula")
def revision(
    body: RevisionCedulaIn,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_it_master_admin),
) -> Any:
    """Cuotas del préstamo más atrasado y depósitos candidatos por mes (no escribe)."""
    return revision_cedula(
        db,
        cedula=body.cedula,
        depositos=[d.model_dump() for d in body.depositos],
        usados=list(body.usados or []),
        tolerancia_pct=body.tolerancia_pct,
        meses_despues=body.meses_despues,
    )


@router.post("/guardar-cedula")
def guardar_cedula(
    body: GuardarCedulaIn,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_it_master_admin),
) -> Any:
    """Registra los depósitos aprobados de una cédula y aplica cascada."""
    return guardar_revision_cedula(
        db,
        cedula=body.cedula,
        prestamo_id=body.prestamo_id,
        depositos=[d.model_dump() for d in body.depositos],
    )
