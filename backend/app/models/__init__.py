"""
Models Module. Export Base y modelos para que Base.metadata conozca las tablas.
"""
from app.core.database import Base
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.ticket import Ticket
from app.models.cuota import Cuota
from app.models.pagos_whatsapp import PagosWhatsapp
from app.models.configuracion import Configuracion
from app.models.auditoria import Auditoria

__all__ = ["Base", "Cliente", "Prestamo", "Ticket", "Cuota", "PagosWhatsapp", "Configuracion", "Auditoria"]

