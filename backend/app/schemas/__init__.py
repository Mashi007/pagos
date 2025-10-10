"""
Schemas de la aplicación
"""

# Importar en orden de dependencias
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse
from app.schemas.prestamo import PrestamoCreate, PrestamoUpdate, PrestamoResponse
from app.schemas.pago import PagoBase, PagoCreate, PagoUpdate, PagoResponse, PagoList

__all__ = [
    # Cliente
    'ClienteCreate',
    'ClienteUpdate', 
    'ClienteResponse',
    # Préstamo
    'PrestamoCreate',
    'PrestamoUpdate',
    'PrestamoResponse',
    # Pago
    'PagoBase',
    'PagoCreate',
    'PagoUpdate',
    'PagoResponse',
    'PagoList',
]
