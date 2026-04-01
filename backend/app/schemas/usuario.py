"""
Schemas para API de usuarios (crear, actualizar, respuesta).
UserResponse se reutiliza desde app.schemas.auth.
Rol: admin | manager | operator | viewer (RBAC estándar).
"""
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

RolType = Literal["admin", "manager", "operator", "viewer"]


class UserCreate(BaseModel):
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre del usuario")
    apellido: str = Field("", max_length=100, description="Apellido del usuario")
    cargo: Optional[str] = Field(None, max_length=100)
    rol: RolType = "viewer"
    is_active: bool = True
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(None, max_length=100)
    cargo: Optional[str] = Field(None, max_length=100)
    rol: Optional[RolType] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)
