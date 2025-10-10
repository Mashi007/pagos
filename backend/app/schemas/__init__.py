# app/schemas/__init__.py
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse, ClienteList
from app.schemas.pago import PagoCreate, PagoUpdate, PagoResponse, PagoList
from app.schemas.common import PaginatedResponse, MessageResponse

__all__ = [
    "ClienteCreate", "ClienteUpdate", "ClienteResponse", "ClienteList",
    "PagoCreate", "PagoUpdate", "PagoResponse", "PagoList",
    "PaginatedResponse", "MessageResponse"
]
