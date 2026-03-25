"""
Catálogo de analistas (tabla analistas).
Gestionado desde /pagos/analistas; los préstamos enlazan por analista_id y replican nombre en prestamos.analista.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class Analista(Base):
    __tablename__ = "analistas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(255), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
