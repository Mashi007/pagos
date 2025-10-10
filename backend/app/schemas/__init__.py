# backend/app/schemas/__init__.py
"""
Schemas centralizados para la API.
Incluye todos los modelos de datos para validación y serialización.
"""
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse
from app.schemas.prestamo import PrestamoCreate, PrestamoUpdate, PrestamoResponse
from app.schemas.pago import PagoCreate, PagoResponse

# Importaciones de user - Schemas completos
from app.schemas.user import (
    # Schemas base de usuario
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserMeResponse,
    
    # Schemas de autenticación
    LoginRequest,
    Token,
    RefreshTokenRequest,
    
    # Schemas de gestión de contraseña
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
)

__all__ = [
    # Cliente
    "ClienteCreate",
    "ClienteUpdate",
    "ClienteResponse",
    
    # Préstamo
    "PrestamoCreate",
    "PrestamoUpdate",
    "PrestamoResponse",
    
    # Pago
    "PagoCreate",
    "PagoResponse",
    
    # Usuario - CRUD
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "UserMeResponse",
    
    # Autenticación y tokens
    "LoginRequest",
    "Token",
    "RefreshTokenRequest",
    
    # Gestión de contraseñas
    "PasswordChange",
    "PasswordReset",
    "PasswordResetConfirm",
]
