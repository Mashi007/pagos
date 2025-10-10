"""
Modelos de la base de datos del servicio de Pagos.
Importar todos los modelos aquí para que Alembic los detecte.
"""

from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago

__all__ = [
    "Cliente",
    "Prestamo",
    "Pago",
]
