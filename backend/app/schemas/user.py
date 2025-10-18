# backend/app/schemas/user.py
"""
Schemas de usuario y autenticación.
Compatible con Pydantic v2.
"""
from typing import Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ============================================
# ENUMS
# ============================================
class UserRole(str, Enum):
    """Roles del sistema - sincronizado con base de datos."""
    USER = "USER"
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    COBRANZAS = "COBRANZAS"


# ============================================
# SCHEMAS BASE
# ============================================
class UserBase(BaseModel):
    """Schema base de usuario (campos comunes)."""
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    cargo: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    rol: UserRole = UserRole.USER


class UserCreate(UserBase):
    """Schema para crear usuario."""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema para actualizar usuario (todos los campos opcionales)."""
    email: Optional[EmailStr] = None
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(None, min_length=1, max_length=100)
    cargo: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    rol: Optional[UserRole] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)


class UserResponse(UserBase):
    """Schema de respuesta de usuario (sin contraseña)."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @property
    def full_name(self) -> str:
        """Retorna el nombre completo del usuario"""
        return f"{self.nombre} {self.apellido}"
    
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Schema para lista de usuarios."""
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class UserMeResponse(BaseModel):
    """Schema para el usuario actual (puede incluir info adicional)."""
    id: int
    email: EmailStr
    nombre: str
    apellido: str
    rol: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    permissions: list[str] = []
    
    model_config = ConfigDict(from_attributes=True)


# ============================================
# SCHEMAS DE AUTENTICACIÓN
# ============================================
class LoginRequest(BaseModel):
    """Schema para solicitud de login."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    """Schema de respuesta de token."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class RefreshTokenRequest(BaseModel):
    """Schema para renovar token."""
    refresh_token: str


# ============================================
# SCHEMAS DE GESTIÓN DE CONTRASEÑAS
# ============================================
class PasswordChange(BaseModel):
    """Schema para cambio de contraseña."""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordReset(BaseModel):
    """Schema para solicitud de reseteo de contraseña."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema para confirmar reseteo de contraseña."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


# ============================================
# EXPORTS
# ============================================
__all__ = [
    "UserRole",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "UserMeResponse",
    "LoginRequest",
    "Token",
    "RefreshTokenRequest",
    "PasswordChange",
    "PasswordReset",
    "PasswordResetConfirm",
]
