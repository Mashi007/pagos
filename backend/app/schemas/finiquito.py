"""Esquemas API Finiquito."""

from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field


class FiniquitoRegistroRequest(BaseModel):
    cedula: str = Field(..., min_length=1, max_length=20)
    email: EmailStr


class FiniquitoRegistroResponse(BaseModel):
    ok: bool
    message: str


class FiniquitoSolicitarCodigoRequest(BaseModel):
    cedula: str = Field(..., min_length=1, max_length=20)
    email: EmailStr


class FiniquitoSolicitarCodigoResponse(BaseModel):
    ok: bool
    message: str


class FiniquitoVerificarCodigoRequest(BaseModel):
    cedula: str = Field(..., min_length=1, max_length=20)
    email: EmailStr
    codigo: str = Field(..., min_length=4, max_length=10)


class FiniquitoVerificarCodigoResponse(BaseModel):
    ok: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    error: Optional[str] = None


class FiniquitoCasoOut(BaseModel):
    id: int
    prestamo_id: int
    cliente_id: Optional[int]
    cedula: str
    total_financiamiento: str
    sum_total_pagado: str
    estado: str
    ultimo_refresh_utc: Optional[str] = None

    class Config:
        from_attributes = True


class FiniquitoCasoListaResponse(BaseModel):
    items: List[FiniquitoCasoOut]


class FiniquitoPatchEstadoRequest(BaseModel):
    estado: str = Field(..., description="REVISION | ACEPTADO | RECHAZADO")


class FiniquitoPatchEstadoResponse(BaseModel):
    ok: bool
    caso: Optional[FiniquitoCasoOut] = None
    error: Optional[str] = None


class FiniquitoDetalleResponse(BaseModel):
    caso: FiniquitoCasoOut
    prestamo: Optional[dict[str, Any]] = None
    cuotas: Optional[List[dict[str, Any]]] = None
