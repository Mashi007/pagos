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
# SCHEMAS DE PAGO
# ============================================
try:
    from app.schemas.pago import (
        PagoCreate,
        PagoListResponse,
        PagoResponse,
        PagoUpdate,
        ResumenCliente,
    )
except ImportError:
    PagoCreate = None  # type: ignore
    PagoUpdate = None  # type: ignore
    PagoResponse = None  # type: ignore
    PagoListResponse = None  # type: ignore
    ResumenCliente = None  # type: ignore

# ============================================
# SCHEMAS DE CONCILIACIÓN BANCARIA
# ============================================
try:
    from app.schemas.conciliacion import (
        ConfirmacionConciliacion,
        ConfirmacionResponse,
        ConciliacionCreate,
        ConciliacionMatch,
        ConciliacionResponse,
        EstadoConciliacion,
        EstadisticasConciliacion,
        ExtractoBancarioUpload,
        FiltroConciliacion,
        MovimientoBancario,
        MovimientoBancarioResponse,
        PagoPendienteConciliacion,
        ReporteConciliacionMensual,
        ResultadoConciliacion,
        TipoMatch,
        ValidacionExtracto,
    )
except ImportError:
    EstadoConciliacion = None  # type: ignore
    TipoMatch = None  # type: ignore
    MovimientoBancario = None  # type: ignore
    MovimientoBancarioResponse = None  # type: ignore
    ConciliacionCreate = None  # type: ignore
    ConciliacionMatch = None  # type: ignore
    ResultadoConciliacion = None  # type: ignore
    ConciliacionResponse = None  # type: ignore
    ConfirmacionConciliacion = None  # type: ignore
    ConfirmacionResponse = None  # type: ignore
    ReporteConciliacionMensual = None  # type: ignore
    FiltroConciliacion = None  # type: ignore
    PagoPendienteConciliacion = None  # type: ignore
    ExtractoBancarioUpload = None  # type: ignore
    ValidacionExtracto = None  # type: ignore
    EstadisticasConciliacion = None  # type: ignore

# ============================================
# SCHEMAS DE KPIs
# ============================================
try:
    from app.schemas.kpis import (
        DashboardKPIs,
        KPIBase,
        KPIConValores,
        KPICreate,
        KPIEstadisticas,
        KPIResponse,
        KPIUpdate,
        KPIValorBase,
        KPIValorCreate,
        KPIValorResponse,
        KPIValorUpdate,
    )
except ImportError:
    KPIBase = None  # type: ignore
    KPICreate = None  # type: ignore
    KPIUpdate = None  # type: ignore
    KPIResponse = None  # type: ignore
    KPIValorBase = None  # type: ignore
    KPIValorCreate = None  # type: ignore
    KPIValorUpdate = None  # type: ignore
    KPIValorResponse = None  # type: ignore
    KPIConValores = None  # type: ignore
    KPIEstadisticas = None  # type: ignore
    DashboardKPIs = None  # type: ignore

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
