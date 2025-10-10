# backend/app/schemas/__init__.py
"""
Schemas centralizados para la API.
Incluye todos los modelos de datos para validación y serialización.

Schemas organizados por módulo:
- Cliente: Gestión de clientes
- Préstamo: Gestión de préstamos
- Pago: Gestión de pagos
- User: Gestión de usuarios y autenticación
"""

# ============================================
# SCHEMAS DE CLIENTE
# ============================================
from app.schemas.cliente import (
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse,
)

# ============================================
# SCHEMAS DE PRÉSTAMO
# ============================================
from app.schemas.prestamo import (
    PrestamoCreate,
    PrestamoUpdate,
    PrestamoResponse,
)

# ============================================
# SCHEMAS DE PAGO
# ============================================
from app.schemas.pago import (
    PagoCreate,
    PagoResponse,
)

# ============================================
# SCHEMAS DE USUARIO Y AUTENTICACIÓN
# ============================================
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


# ============================================
# EXPORTS PÚBLICOS
# ============================================
__all__ = [
    # ========== CLIENTE ==========
    "ClienteCreate",
    "ClienteUpdate",
    "ClienteResponse",
    
    # ========== PRÉSTAMO ==========
    "PrestamoCreate",
    "PrestamoUpdate",
    "PrestamoResponse",
    
    # ========== PAGO ==========
    "PagoCreate",
    "PagoResponse",
    
    # ========== USUARIO - CRUD ==========
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "UserMeResponse",
    
    # ========== AUTENTICACIÓN ==========
    "LoginRequest",
    "Token",
    "RefreshTokenRequest",
    
    # ========== GESTIÓN DE CONTRASEÑAS ==========
    "PasswordChange",
    "PasswordReset",
    "PasswordResetConfirm",
]


# ============================================
# INFORMACIÓN DEL MÓDULO
# ============================================
__version__ = "1.0.0"
__author__ = "Sistema de Gestión de Préstamos"
__description__ = "Schemas Pydantic v2 para validación de API"
