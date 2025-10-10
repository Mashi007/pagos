# backend/app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base de usuario"""
    email: EmailStr
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    rol: str = Field(..., description="ADMIN, ASESOR, COBRANZAS, CONTADOR")


class UserCreate(UserBase):
    """Crear usuario"""
    password: str = Field(..., min_length=8, description="Mínimo 8 caracteres")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@example.com",
                "nombre": "Juan",
                "apellido": "Pérez",
                "rol": "ASESOR",
                "password": "password123"
            }
        }


class UserUpdate(BaseModel):
    """Actualizar usuario"""
    email: Optional[EmailStr] = None
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    apellido: Optional[str] = Field(None, min_length=2, max_length=100)
    rol: Optional[str] = None
    activo: Optional[bool] = None


class UserResponse(BaseModel):
    """Respuesta de usuario"""
    id: int
    email: str
    nombre: str
    apellido: str
    rol: str
    activo: bool
    fecha_creacion: datetime
    ultima_conexion: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Lista de usuarios"""
    total: int
    usuarios: list[UserResponse]
