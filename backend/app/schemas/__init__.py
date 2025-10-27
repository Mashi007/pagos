"""
backend/app/schemas/__init__.py

Módulo de schemas Pydantic para validación de API:
- Cliente: Gestión de clientes
- Conciliación: Conciliación bancaria
- KPIs: Métricas e indicadores
"""

# ============================================
# SCHEMAS DE CLIENTE
# ============================================
from app.schemas.cliente import ClienteCreate, ClienteResponse, ClienteUpdate

# ============================================
# SCHEMAS DE PRÉSTAMO
# ============================================
from app.schemas.prestamo import (
    PrestamoAuditoriaResponse,
    PrestamoCreate,
    PrestamoEvaluacionCreate,
    PrestamoEvaluacionResponse,
    PrestamoResponse,
    PrestamoUpdate,
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
    "PrestamoEvaluacionCreate",
    "PrestamoEvaluacionResponse",
    "PrestamoAuditoriaResponse",
]

# ============================================
# INFORMACIÓN DEL MÓDULO
# ============================================
__version__ = "1.0.0"
__description__ = (
    "Schemas Pydantic v2 para validación de API - SIMPLIFICADO (sin UserRole)"
)
