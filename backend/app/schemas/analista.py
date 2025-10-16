from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime

class AnalistaBase(BaseModel):
    nombre: str
    apellido: Optional[str] = ""
    email: Optional[str] = ""
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

    @field_validator('comision_porcentaje')
    @classmethod
    def comision_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('La comisión debe estar entre 0 y 100')
        return v

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

    @field_validator('comision_porcentaje')
    @classmethod
    def comision_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('La comisión debe estar entre 0 y 100')
        return v

class AnalistaResponse(AnalistaBase):
    id: int
    nombre_completo: str
    created_at: datetime
    
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class AnalistaListResponse(BaseModel):
    items: List[AnalistaResponse]
    total: int
    page: int
    size: int
    pages: int
