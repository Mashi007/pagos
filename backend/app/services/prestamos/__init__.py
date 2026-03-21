"""Servicios especializados para gestión de préstamos."""

from .prestamos_service import PrestamosService
from .prestamos_validacion import PrestamosValidacion
from .prestamos_calculo import PrestamosCalculo
from .amortizacion_service import AmortizacionService
from .prestamos_excepciones import (
    PrestamoNotFoundError,
    PrestamoValidationError,
    PrestamoConflictError,
    PrestamoStateError,
    ClienteNotFoundError,
    ClienteConErrorError,
    AmortizacionCalculoError,
    CuotaNotFoundError,
    CuotaPagoConflictError,
    TasaCambioNotFoundError,
    EstadoCuentaGenerationError,
)
from .adaptador_compatibility import (
    con_manejo_errores_prestamos,
    obtener_servicio_prestamos,
    AdaptadorPrestamosLegacy,
    validar_prestamo_existente,
    validar_cliente_existe_endpoint,
)

__all__ = [
    # Services
    "PrestamosService",
    "PrestamosValidacion",
    "PrestamosCalculo",
    "AmortizacionService",
    # Exceptions
    "PrestamoNotFoundError",
    "PrestamoValidationError",
    "PrestamoConflictError",
    "PrestamoStateError",
    "ClienteNotFoundError",
    "ClienteConErrorError",
    "AmortizacionCalculoError",
    "CuotaNotFoundError",
    "CuotaPagoConflictError",
    "TasaCambioNotFoundError",
    "EstadoCuentaGenerationError",
    # Compatibility
    "con_manejo_errores_prestamos",
    "obtener_servicio_prestamos",
    "AdaptadorPrestamosLegacy",
    "validar_prestamo_existente",
    "validar_cliente_existe_endpoint",
]
