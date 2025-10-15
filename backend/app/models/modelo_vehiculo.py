# backend/app/models/modelo_vehiculo.py
"""
Modelo SQLAlchemy para modelos de vehículos configurables
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric
from sqlalchemy.sql import func
from app.db.base import Base


class ModeloVehiculo(Base):
    __tablename__ = "modelos_vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    marca = Column(String(50), nullable=False, index=True)
    modelo = Column(String(100), nullable=False)
    nombre_completo = Column(String(150), nullable=False, unique=True)
    categoria = Column(String(50), nullable=True, index=True)  # Sedán, SUV, Hatchback, Motocicleta, etc.
    precio_base = Column(Numeric(12, 2), nullable=True)
    activo = Column(Boolean, nullable=False, default=True, index=True)
    descripcion = Column(Text, nullable=True)
    especificaciones = Column(Text, nullable=True)  # JSON como texto para compatibilidad
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ModeloVehiculo(id={self.id}, nombre='{self.nombre_completo}', activo={self.activo})>"

    @property
    def es_motocicleta(self):
        """Verificar si es una motocicleta"""
        return self.categoria and 'moto' in self.categoria.lower()

    @property
    def es_vehiculo_liviano(self):
        """Verificar si es un vehículo liviano (no motocicleta)"""
        return not self.es_motocicleta

    @classmethod
    def get_activos_por_categoria(cls, db, categoria=None):
        """Obtener modelos activos por categoría"""
        query = db.query(cls).filter(cls.activo == True)
        if categoria:
            query = query.filter(cls.categoria == categoria)
        return query.order_by(cls.marca, cls.modelo).all()

    @classmethod
    def get_por_marca(cls, db, marca, activo_only=True):
        """Obtener modelos por marca"""
        query = db.query(cls).filter(cls.marca == marca)
        if activo_only:
            query = query.filter(cls.activo == True)
        return query.order_by(cls.modelo).all()
