# backend/app/schemas/user.py
"""
Schemas de usuario y autenticación.
Incluye modelos base, CRUD y tokens JWT.
"""

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


# ============================================================================
# SCHEMAS DE AUTENTICACIÓN
# ============================================================================

class LoginRequest(BaseModel):
    """Request de login"""
    email: EmailStr
    password: str = Field(..., min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@example.com",
                "password": "password123"
            }
        }


class Token(BaseModel):
    """Respuesta de token JWT"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Segundos hasta expiración")
    refresh_token: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request para refrescar token"""
    refresh_token: str = Field(..., description="Token de refresco")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class UserProfile(BaseModel):
    """Perfil completo de usuario autenticado"""
    id: int
    email: str
    nombre: str
    apellido: str
    rol: str
    activo: bool
    fecha_creacion: datetime
    ultima_conexion: Optional[datetime] = None
    permisos: list[str] = Field(default_factory=list, description="Lista de permisos del usuario")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "admin@example.com",
                "nombre": "Admin",
                "apellido": "Sistema",
                "rol": "ADMIN",
                "activo": True,
                "fecha_creacion": "2025-01-01T00:00:00",
                "ultima_conexion": "2025-10-10T15:00:00",
                "permisos": ["users:read", "users:write", "loans:admin"]
            }
        }


class PasswordChange(BaseModel):
    """Cambio de contraseña"""
    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña (mínimo 8 caracteres)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newpassword456"
            }
        }


class PasswordReset(BaseModel):
    """Reset de contraseña"""
    email: EmailStr = Field(..., description="Email del usuario")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@example.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """Confirmación de reset de contraseña"""
    token: str = Field(..., description="Token de reset recibido por email")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123xyz789",
                "new_password": "newsecurepassword123"
            }
        }
