from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime

class AsesorBase(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    telefono: Optional[str] = None
    especialidad: Optional[str] = None
    comision_porcentaje: Optional[int] = None
    activo: bool = True
    notas: Optional[str] = None

    @validator('nombre', 'apellido')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre y apellido no pueden estar vacíos')
        return v.strip()

    @validator('comision_porcentaje')
    def comision_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('La comisión debe estar entre 0 y 100')
        return v

class AsesorCreate(AsesorBase):
    pass

class AsesorUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    especialidad: Optional[str] = None
    comision_porcentaje: Optional[int] = None
    activo: Optional[bool] = None
    notas: Optional[str] = None

    @validator('nombre', 'apellido')
    def name_must_not_be_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('El nombre y apellido no pueden estar vacíos')
        return v.strip() if v else v

    @validator('comision_porcentaje')
    def comision_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('La comisión debe estar entre 0 y 100')
        return v

class AsesorResponse(AsesorBase):
    id: int
    nombre_completo: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AsesorListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    data: List[AsesorResponse]
