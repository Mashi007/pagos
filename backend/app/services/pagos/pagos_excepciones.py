"""Excepciones específicas para servicios de pagos."""


class PagoError(Exception):
    """Excepción base para errores de pagos."""
    pass


class PagoNotFoundError(PagoError):
    """El pago no fue encontrado."""
    def __init__(self, pago_id: int):
        self.pago_id = pago_id
        super().__init__(f"Pago {pago_id} no encontrado")


class PagoValidationError(PagoError):
    """Error en la validación de datos de pago."""
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Error en {field}: {message}")


class PagoConflictError(PagoError):
    """Conflicto al procesar el pago (documento duplicado, etc)."""
    def __init__(self, message: str):
        super().__init__(message)


class ClienteNotFoundError(PagoError):
    """Cliente no encontrado."""
    def __init__(self, cliente_id: int):
        self.cliente_id = cliente_id
        super().__init__(f"Cliente {cliente_id} no encontrado")


class CuentaNotFoundError(PagoError):
    """Cuenta no encontrada."""
    def __init__(self, cuenta_id: int):
        self.cuenta_id = cuenta_id
        super().__init__(f"Cuenta {cuenta_id} no encontrada")


class PrestamoNotFoundError(PagoError):
    """Préstamo no encontrado."""
    def __init__(self, prestamo_id: int):
        self.prestamo_id = prestamo_id
        super().__init__(f"Préstamo {prestamo_id} no encontrado")
