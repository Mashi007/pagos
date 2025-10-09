# app/models/__init__.py
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo, EstadoPrestamo, ModalidadPago
from app.models.pago import Pago

__all__ = ["Cliente", "Prestamo", "Pago", "EstadoPrestamo", "ModalidadPago"]
