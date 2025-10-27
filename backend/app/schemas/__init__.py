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
# SCHEMAS DE USUARIO Y AUTENTICACIÓN
# ============================================
# NOTA: UserRole eliminado - ahora se usa is_admin boolean

# ============================================
# SCHEMAS DE CONCILIACIÓN BANCARIA
# ============================================
# from app.schemas.conciliacion import

# ============================================
# SCHEMAS DE KPIs
# ============================================
# ACTUALIZADO: Importaciones corregidas para coincidir con kpis.py
# from app.schemas.kpis import

# ============================================
# SCHEMAS DE PAGO
# ============================================
# from app.schemas.pago import

# ============================================
# SCHEMAS DE PRÉSTAMO
# ============================================
from app.schemas.prestamo import (
    PrestamoCreate,
    PrestamoResponse,
    PrestamoUpdate,
    PrestamoEvaluacionCreate,
    PrestamoEvaluacionResponse,
    PrestamoAuditoriaResponse,
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
    # ========== PAGO ==========
    "PagoCreate",
    "PagoUpdate",
    "PagoResponse",
    "PagoListResponse",
    "ResumenCliente",
    # ========== USUARIO ==========
    # NOTA: UserRole eliminado - ahora se usa is_admin boolean
    # están disponibles directamente desde app.schemas.user
    # ========== CONCILIACIÓN ==========
    "EstadoConciliacion",
    "TipoMatch",
    "MovimientoBancario",
    "MovimientoBancarioResponse",
    "ConciliacionCreate",
    "ConciliacionMatch",
    "ResultadoConciliacion",
    "ConciliacionResponse",
    "ConfirmacionConciliacion",
    "ConfirmacionResponse",
    "ReporteConciliacionMensual",
    "FiltroConciliacion",
    "PagoPendienteConciliacion",
    "ExtractoBancarioUpload",
    "ValidacionExtracto",
    "EstadisticasConciliacion",
    # ========== KPIs (ACTUALIZADO) ==========
    "KPIBase",
    "KPICreate",
    "KPIUpdate",
    "KPIResponse",
    "KPIValorBase",
    "KPIValorCreate",
    "KPIValorUpdate",
    "KPIValorResponse",
    "KPIConValores",
    "KPIEstadisticas",
    "DashboardKPIs",
]

# ============================================
# INFORMACIÓN DEL MÓDULO
# ============================================
__version__ = "1.0.0"
__description__ = (
    "Schemas Pydantic v2 para validación de API - SIMPLIFICADO (sin UserRole)"
)
