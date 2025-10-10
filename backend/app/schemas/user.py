# backend/app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

from app.core.constants import Roles, EstadoUsuario


# Schemas base
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    nombre_completo: str = Field(..., min_length=3, max_length=100)
    telefono: Optional[str] = None
    rol: Roles = Roles.ASESOR
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """Validar que el username sea alfanumérico"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('El username solo puede contener letras, números, guiones y guiones bajos')
        return v.lower()


class UserCreate(UserBase):
    """Schema para crear usuario"""
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        """Validar fortaleza de contraseña"""
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class UserUpdate(BaseModel):
    """Schema para actualizar usuario"""
    email: Optional[EmailStr] = None
    nombre_completo: Optional[str] = Field(None, min_length=3, max_length=100)
    telefono: Optional[str] = None
    rol: Optional[Roles] = None
    estado: Optional[EstadoUsuario] = None
    avatar_url: Optional[str] = None


class UserChangePassword(BaseModel):
    """Schema para cambiar contraseña"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validar fortaleza de contraseña"""
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class UserResetPassword(BaseModel):
    """Schema para resetear contraseña (admin)"""
    new_password: str = Field(..., min_length=8)
    debe_cambiar_password: bool = True


class UserResponse(UserBase):
    """Schema de respuesta de usuario"""
    id: int
    estado: EstadoUsuario
    is_superuser: bool
    debe_cambiar_password: bool
    ultimo_login: Optional[datetime] = None
    avatar_url: Optional[str] = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    
    class Config:
        from_attributes = True


class UserList(BaseModel):
    """Schema para lista de usuarios"""
    usuarios: list[UserResponse]
    total: int
    pagina: int
    total_paginas: int


class UserProfile(BaseModel):
    """Schema para perfil de usuario"""
    id: int
    email: EmailStr
    username: str
    nombre_completo: str
    telefono: Optional[str] = None
    rol: Roles
    estado: EstadoUsuario
    avatar_url: Optional[str] = None
    ultimo_login: Optional[datetime] = None
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True


# Schemas de autenticación
class Token(BaseModel):
    """Schema de token JWT"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Payload del token"""
    sub: int  # user_id
    exp: datetime
    type: str  # "access" o "refresh"


class LoginRequest(BaseModel):
    """Schema para login"""
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    """Schema para refresh token"""
    refresh_token: str
