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
# IMPORTAR SOLO LOS MODELOS QUE REALMENTE EXISTEN
try:
    from app.schemas.user import (
        UserRole,  # Este existe según el error
        # Descomentar solo los que realmente existan en user.py:
        # UserBase,
        # UserCreate,
        # UserUpdate,
        # UserResponse,
    )
except ImportError as e:
    print(f"⚠️  Advertencia: Algunos modelos de usuario no están disponibles: {e}")
    UserRole = None

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
    
    # ========== USUARIO ==========
    "UserRole",
]

# ============================================
# INFORMACIÓN DEL MÓDULO
# ============================================
__version__ = "1.0.0"
__author__ = "Sistema de Gestión de Préstamos"
__description__ = "Schemas Pydantic v2 para validación de API"
