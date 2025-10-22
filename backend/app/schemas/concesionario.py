from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

class ConcesionarioBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=255, description="Nombre del concesionario")
    activo: bool = Field(True, description="Estado activo del concesionario")

class ConcesionarioCreate(ConcesionarioBase):
    pass

class ConcesionarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=255)
    activo: Optional[bool] = None

class ConcesionarioResponse(ConcesionarioBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    fecha_eliminacion: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ConcesionarioListResponse(BaseModel):
    items: list[ConcesionarioResponse]
    total: int
    page: int
    size: int
    pages: int
