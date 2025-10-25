from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.session import Base


class Concesionario(Base):

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    activo = Column(Boolean, default=True, nullable=False)

    # Timestamps
    updated_at = Column(
    )


    def __repr__(self):
        return (
            f"<Concesionario(id={self.id}, nombre='{self.nombre}', "
            f"activo={self.activo})>"
        )


    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "activo": self.activo,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
            "fecha_eliminacion": (
                self.fecha_eliminacion.isoformat()
                if self.fecha_eliminacion
                else None
            ),
        }
