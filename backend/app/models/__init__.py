"""
Models Module. Export Base y modelos para que Base.metadata conozca las tablas.
"""
from app.core.database import Base
from app.models.cliente import Cliente
from app.models.ticket import Ticket
from app.models.cuota import Cuota

__all__ = ["Base", "Cliente", "Ticket", "Cuota"]

