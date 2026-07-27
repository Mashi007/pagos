"""
Catálogo de concesionarios (tabla concesionarios).
Gestionado desde /pagos/concesionarios; los préstamos enlazan por concesionario_id
y replican el nombre en prestamos.concesionario.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class Concesionario(Base):
    __tablename__ = "concesionarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(255), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
