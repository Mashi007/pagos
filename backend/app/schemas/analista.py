from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator, ConfigDict

class AnalistaBase(BaseModel):
    nombre: str  # Nombre completo (incluye apellido)
    apellido: Optional[str] = ''
    email: Optional[str] = None
    telefono: Optional[str] = None
    especialidad: Optional[str] = None
    comision_porcentaje: Optional[int] = None
    activo: bool = True
    notas: Optional[str] = None

    @field_validator('nombre')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        return v.strip()

class AnalistaCreate(AnalistaBase):
    pass

class AnalistaUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    especialidad: Optional[str] = None
    comision_porcentaje: Optional[int] = None
    activo: Optional[bool] = None
    notas: Optional[str] = None

    @field_validator('nombre')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('El nombre no puede estar vacío')
        return v.strip() if v else v

class AnalistaResponse(AnalistaBase):
    id: int
    nombre_completo: str
    primer_nombre: str
    updated_at: Optional[datetime] = None
    fecha_eliminacion: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AnalistaListResponse(BaseModel):
    items: List[AnalistaResponse]
    total: int
    page: int
    size: int
    pages: int
