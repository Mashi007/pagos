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
    MAX_PRESTAMOS_LOTE,
    procesar_lote_seriales,
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


@router.post("/procesar-lote")
def procesar_lote(
    body: LoteSerialesIn,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_it_master_admin),
) -> Any:
    """Procesa hasta 20 cédulas; devuelve pagos creados y depósitos consumidos."""
    return procesar_lote_seriales(
        db,
        cedulas=list(body.cedulas),
        depositos=[d.model_dump() for d in body.depositos],
        usados=list(body.usados or []),
    )
