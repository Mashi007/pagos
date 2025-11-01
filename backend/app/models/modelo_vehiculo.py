from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String

from app.db.session import Base


class ModeloVehiculo(Base):
    """
    Modelo para modelos de vehículos
    Representa los diferentes modelos de vehículos disponibles
    """

    __tablename__ = "modelos_vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    modelo = Column(String(100), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True, index=True)
    # Precio del activo (moneda única definida en configuración general)
    precio = Column(Numeric(15, 2), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    fecha_actualizacion = Column(DateTime(timezone=True), nullable=True)
    actualizado_por = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<ModeloVehiculo(id={self.id}, modelo='{self.modelo}', activo={self.activo})>"

    def to_dict(self):
        return {
            "id": self.id,
            "modelo": self.modelo,
            "activo": self.activo,
            "precio": float(self.precio) if self.precio is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fecha_actualizacion": (self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None),
            "actualizado_por": self.actualizado_por,
        }
