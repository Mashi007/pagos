from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.session import Base


class Concesionario(Base):
    __tablename__ = "concesionarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    activo = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    fecha_eliminacion = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return (
            f"<Concesionario(id="
            f"{self.id}"
            f", nombre='{self.nombre}', activo={
            self.activo})>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "activo": self.activo,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
            "fecha_eliminacion": (
                self.fecha_eliminacion.isoformat() if self.fecha_eliminacion else None
            ),
        }
