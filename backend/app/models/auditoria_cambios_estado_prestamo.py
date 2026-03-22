"""
Mapeo de la tabla auditoria_cambios_estado_prestamo (historial de cambios de estado del prestamo).
Solo se declaran columnas necesarias para consultas / borrado en cascada logica.
"""
from sqlalchemy import Column, Integer

from app.core.database import Base


class AuditoriaCambiosEstadoPrestamo(Base):
    __tablename__ = "auditoria_cambios_estado_prestamo"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prestamo_id = Column(Integer, nullable=False, index=True)
