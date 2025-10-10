# app/schemas/__init__.py
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse, ClienteList
from app.schemas.prestamo import PrestamoCreate, PrestamoUpdate, PrestamoResponse, PrestamoList
from app.schemas.pago import PagoCreate, PagoUpdate, PagoResponse, PagoList
from app.schemas.common import PaginatedResponse, MessageResponse

__all__ = [
    "ClienteCreate", "ClienteUpdate", "ClienteResponse", "ClienteList",
    "PrestamoCreate", "PrestamoUpdate", "PrestamoResponse", "PrestamoList",
    "PagoCreate", "PagoUpdate", "PagoResponse", "PagoList",
    "PaginatedResponse", "MessageResponse"
]
