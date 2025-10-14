# backend/app/schemas/__init__.py
"""
Schemas centralizados para la API.
Incluye todos los modelos de datos para validación y serialización.
Schemas organizados por módulo:
- Cliente: Gestión de clientes
- Préstamo: Gestión de préstamos
- Pago: Gestión de pagos
- User: Gestión de usuarios y autenticación
- Conciliación: Conciliación bancaria
- KPIs: Métricas e indicadores
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
    UserRole,
)
# ============================================
# SCHEMAS DE CONCILIACIÓN BANCARIA
# ============================================
from app.schemas.conciliacion import (
    EstadoConciliacion,
    TipoMatch,
    MovimientoBancario,
    MovimientoBancarioResponse,
    ConciliacionCreate,
    ConciliacionMatch,
    ResultadoConciliacion,
    ConciliacionResponse,
    ConfirmacionConciliacion,
    ConfirmacionResponse,
    ReporteConciliacionMensual,
    FiltroConciliacion,
    PagoPendienteConciliacion,
    ExtractoBancarioUpload,
    ValidacionExtracto,
    EstadisticasConciliacion,
)
# ============================================
# SCHEMAS DE KPIs
# ============================================
# ACTUALIZADO: Importaciones corregidas para coincidir con kpis.py
from app.schemas.kpis import (
    KPIBase,
    KPICreate,
    KPIUpdate,
    KPIResponse,
    KPIValorBase,
    KPIValorCreate,
    KPIValorUpdate,
    KPIValorResponse,
    KPIConValores,
    KPIEstadisticas,
    DashboardKPIs,
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
    
    # ========== USUARIO ==========
    "UserRole",
    
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
__author__ = "Sistema de Gestión de Préstamos"
__description__ = "Schemas Pydantic v2 para validación de API"
