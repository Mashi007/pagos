# backend/app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Schema base para Usuario"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    nombre_completo: str = Field(..., min_length=3)
    telefono: Optional[str] = None
    rol: str = "ASESOR"  # ADMIN, COBRANZAS, ASESOR, VALIDADOR, SOLO_LECTURA


class UserCreate(UserBase):
    """Schema para crear usuario"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema para actualizar usuario"""
    email: Optional[EmailStr] = None
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None
    rol: Optional[str] = None


class UserResponse(UserBase):
    """Schema para respuesta de usuario"""
    id: int
    estado: str
    is_superuser: bool
    fecha_creacion: datetime
    ultimo_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfile(UserResponse):
    """Schema para perfil completo de usuario"""
    avatar_url: Optional[str] = None
    debe_cambiar_password: bool


class Token(BaseModel):
    """Schema para token JWT"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Schema para login"""
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    """Schema para refresh token"""
    refresh_token: str
