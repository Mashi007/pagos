from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime

class ConcesionarioBase(BaseModel):
    nombre: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    responsable: Optional[str] = None
    activo: bool = True

    @validator('nombre')
    def nombre_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre del concesionario no puede estar vacío')
        return v.strip()

class ConcesionarioCreate(ConcesionarioBase):
    pass

class ConcesionarioUpdate(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    responsable: Optional[str] = None
    activo: Optional[bool] = None

    @validator('nombre')
    def nombre_must_not_be_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('El nombre del concesionario no puede estar vacío')
        return v.strip() if v else v

class ConcesionarioResponse(ConcesionarioBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ConcesionarioListResponse(BaseModel):
    items: List[ConcesionarioResponse]
    total: int
    page: int
    size: int
    pages: int
