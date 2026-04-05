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
    ultima_fecha_pago: Optional[str] = Field(
        default=None,
        description="Ultima fecha_pago en tabla pagos para este prestamo_id (MAX).",
    )
    contacto_para_siguientes: Optional[bool] = Field(
        default=None,
        description="Si estado=TERMINADO: respuesta Sí/No a contacto para pasos siguientes.",
    )
    cliente_nombres: Optional[str] = None
    cliente_email: Optional[str] = None
    cliente_telefono: Optional[str] = None

    class Config:
        from_attributes = True


class FiniquitoConteoRevisionNuevosResponse(BaseModel):
    """Casos en REVISION creados recientemente (al materializarse como LIQUIDADO elegible)."""

    total: int = Field(
        ...,
        ge=0,
        description="Cantidad en revision dentro de la ventana temporal.",
    )
    ventana_horas: int = Field(
        ...,
        ge=1,
        description="Horas hacia atras desde ahora (UTC) usadas en el conteo.",
    )


class FiniquitoCasoListaResponse(BaseModel):
    items: List[FiniquitoCasoOut]
    total: int = Field(
        ...,
        description="Total de filas que coinciden con el filtro (sin paginar).",
    )
    limit: int = Field(
        ...,
        description="Tamano de pagina efectivo (admin) o filas devueltas (publico sin paginar).",
    )
    offset: int = Field(..., description="Desplazamiento desde el mas reciente (orden id desc).")


class FiniquitoPatchEstadoRequest(BaseModel):
    estado: str = Field(
        ...,
        description="REVISION | ACEPTADO | RECHAZADO | EN_PROCESO | TERMINADO | ANTIGUO",
    )
    contacto_para_siguientes: Optional[bool] = Field(
        None,
        description=(
            "Al pasar a TERMINADO: obligatorio si venia de EN_PROCESO; "
            "opcional si venia de ACEPTADO (por defecto false)."
        ),
    )
    nota_antiguo: Optional[str] = Field(
        None,
        max_length=4000,
        description=(
            "Si estado=ANTIGUO y la ultima fecha de pago es posterior a 2026-01-01 (o no hay fecha), "
            "obligatoria (min. 15 caracteres). Opcional si ultima fecha <= 2026-01-01."
        ),
    )


class FiniquitoPatchEstadoResponse(BaseModel):
    ok: bool
    caso: Optional[FiniquitoCasoOut] = None
    error: Optional[str] = None


class FiniquitoDetalleResponse(BaseModel):
    caso: FiniquitoCasoOut
    prestamo: Optional[dict[str, Any]] = None
    cuotas: Optional[List[dict[str, Any]]] = None
