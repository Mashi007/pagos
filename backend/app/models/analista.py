"""
Modelo de Analista
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db.session import Base


class Analista(Base):
    """
    Modelo para analistas del sistema
    Representa a los analistas que pueden gestionar clientes y préstamos
    """

    __tablename__ = "analistas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(
        String(255), nullable=False, index=True
    )  # Nombre completo (incluye apellido)
    activo = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=True
    )
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Analista(id={self.id}, nombre='{self.nombre}', activo={self.activo})>"

    @property
    def nombre_completo(self):
        """Retorna el nombre completo (que ya está en la columna nombre)"""
        return self.nombre

    def to_dict(self):
        """Convierte el analista a diccionario"""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "activo": self.activo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
