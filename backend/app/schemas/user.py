# backend/app/schemas/user.py
"""
Schemas de Usuario: Create, Update, Response, Authentication y Password Management
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.core.permissions import UserRole


# ============================================
# SCHEMAS BASE DE USUARIO
# ============================================

class UserBase(BaseModel):
    """Schema base de usuario"""
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    rol: UserRole
    is_active: bool = True


class UserCreate(UserBase):
    """Schema para crear usuario"""
    password: str = Field(..., min_length=8, description="Contraseña del usuario")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@sistema.com",
                "nombre": "Juan",
                "apellido": "Pérez",
                "rol": "ASESOR",
                "password": "Password123!",
                "is_active": True
            }
        }


class UserUpdate(BaseModel):
    """Schema para actualizar usuario"""
    email: Optional[EmailStr] = None
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(None, min_length=1, max_length=100)
    rol: Optional[UserRole] = None
    is_active: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan Carlos",
                "apellido": "Pérez López",
                "rol": "COBRANZAS"
            }
        }


class UserResponse(UserBase):
    """Schema para respuesta de usuario (sin password)"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "usuario@sistema.com",
                "nombre": "Juan",
                "apellido": "Pérez",
                "rol": "ASESOR",
                "is_active": True,
                "created_at": "2025-10-10T10:00:00",
                "updated_at": "2025-10-10T15:30:00",
                "last_login": "2025-10-10T16:45:00"
            }
        }


class UserListResponse(BaseModel):
    """Schema para lista de usuarios"""
    users: list[UserResponse]
    total: int
    page: int = 1
    page_size: int = 10
    
    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "id": 1,
                        "email": "admin@sistema.com",
                        "nombre": "Admin",
                        "apellido": "Sistema",
                        "rol": "ADMIN",
                        "is_active": True,
                        "created_at": "2025-10-10T10:00:00"
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10
            }
        }


class UserMeResponse(UserResponse):
    """Schema para respuesta de usuario actual (con info adicional)"""
    permissions: list[str] = []
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "admin@sistema.com",
                "nombre": "Admin",
                "apellido": "Sistema",
                "rol": "ADMIN",
                "is_active": True,
                "created_at": "2025-10-10T10:00:00",
                "last_login": "2025-10-10T16:45:00",
                "permissions": [
                    "user:create",
                    "user:read",
                    "cliente:create",
                    "prestamo:approve"
                ]
            }
        }


# ============================================
# SCHEMAS DE AUTENTICACIÓN
# ============================================

class LoginRequest(BaseModel):
    """Schema para login de usuario"""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@sistema.com",
                "password": "Password123!"
            }
        }


class Token(BaseModel):
    """Schema para respuesta de token JWT"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class RefreshTokenRequest(BaseModel):
    """Schema para renovar token"""
    refresh_token: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


# ============================================
# SCHEMAS DE GESTIÓN DE CONTRASEÑAS
# ============================================

class PasswordChange(BaseModel):
    """Schema para cambio de contraseña"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPassword123!",
                "new_password": "NewPassword456!"
            }
        }


class PasswordReset(BaseModel):
    """Schema para solicitar reset de contraseña"""
    email: EmailStr
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@sistema.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """Schema para confirmar reset de contraseña"""
    token: str
    new_password: str = Field(..., min_length=8)
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123def456",
                "new_password": "NewPassword789!"
            }
        }
