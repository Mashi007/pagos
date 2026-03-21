"""Excepciones específicas para servicios de préstamos."""


class PrestamoError(Exception):
    """Excepción base para errores de préstamos."""
    pass


class PrestamoNotFoundError(PrestamoError):
    """El préstamo no fue encontrado."""
    def __init__(self, prestamo_id: int):
        self.prestamo_id = prestamo_id
        super().__init__(f"Préstamo {prestamo_id} no encontrado")


class PrestamoValidationError(PrestamoError):
    """Error en la validación de datos de préstamo."""
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Error en {field}: {message}")


class PrestamoConflictError(PrestamoError):
    """Conflicto al procesar el préstamo."""
    def __init__(self, message: str):
        super().__init__(message)


class PrestamoStateError(PrestamoError):
    """Error de transición de estado inválida."""
    def __init__(self, estado_actual: str, estado_intentado: str):
        self.estado_actual = estado_actual
        self.estado_intentado = estado_intentado
        super().__init__(
            f"No se puede cambiar de {estado_actual} a {estado_intentado}"
        )


class ClienteNotFoundError(PrestamoError):
    """Cliente no encontrado."""
    def __init__(self, cliente_id: int):
        self.cliente_id = cliente_id
        super().__init__(f"Cliente {cliente_id} no encontrado")


class ClienteConErrorError(PrestamoError):
    """Cliente tiene errores registrados y no puede obtener crédito."""
    def __init__(self, cliente_id: int, mensaje: str = ""):
        self.cliente_id = cliente_id
        super().__init__(f"Cliente {cliente_id} con errores: {mensaje}")


class AmortizacionCalculoError(PrestamoError):
    """Error en el cálculo de amortización."""
    def __init__(self, message: str):
        super().__init__(f"Error en cálculo de amortización: {message}")


class CuotaNotFoundError(PrestamoError):
    """Cuota de préstamo no encontrada."""
    def __init__(self, cuota_id: int):
        self.cuota_id = cuota_id
        super().__init__(f"Cuota {cuota_id} no encontrada")


class CuotaPagoConflictError(PrestamoError):
    """Conflicto en pago de cuota."""
    def __init__(self, cuota_id: int, message: str):
        self.cuota_id = cuota_id
        super().__init__(f"Conflicto en cuota {cuota_id}: {message}")


class TasaCambioNotFoundError(PrestamoError):
    """Tasa de cambio no disponible."""
    def __init__(self, message: str = ""):
        super().__init__(
            f"Tasa de cambio no disponible{': ' + message if message else ''}"
        )


class EstadoCuentaGenerationError(PrestamoError):
    """Error al generar estado de cuenta del préstamo."""
    def __init__(self, prestamo_id: int, message: str = ""):
        self.prestamo_id = prestamo_id
        super().__init__(
            f"Error generando estado de cuenta para préstamo {prestamo_id}: {message}"
        )
