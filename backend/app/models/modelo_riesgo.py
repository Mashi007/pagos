"""
Modelo de Modelo de Riesgo ML
Almacena metadatos de modelos de machine learning entrenados
"""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ModeloRiesgo(Base):
    """
    Modelo de machine learning para predicción de riesgo crediticio
    """

    __tablename__ = "modelos_riesgo"

    id = Column(Integer, primary_key=True, index=True)

    # Información del modelo
    nombre = Column(String(200), nullable=False)
    version = Column(String(50), nullable=False, default="1.0.0")
    algoritmo = Column(String(100), nullable=False)  # random_forest, xgboost, etc.

    # Métricas de rendimiento
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    roc_auc = Column(Float, nullable=True)

    # Información de entrenamiento
    ruta_archivo = Column(String(500), nullable=False)  # Ruta al archivo .pkl
    total_datos_entrenamiento = Column(Integer, nullable=True)
    total_datos_test = Column(Integer, nullable=True)

    # Parámetros de entrenamiento
    test_size = Column(Float, nullable=True)  # 0.2 = 20%
    random_state = Column(Integer, nullable=True)

    # Estado
    activo = Column(Boolean, default=False, nullable=False, index=True)

    # Relación opcional con usuario que entrenó el modelo
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Metadatos adicionales
    descripcion = Column(Text, nullable=True)
    features_usadas = Column(Text, nullable=True)  # Lista de features separadas por coma

    # Relación ORM
    usuario = relationship("User", foreign_keys=[usuario_id])

    # Auditoría
    entrenado_en = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    activado_en = Column(DateTime, nullable=True)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<ModeloRiesgo {self.nombre} v{self.version} - {self.algoritmo}>"

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "version": self.version,
            "algoritmo": self.algoritmo,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "roc_auc": self.roc_auc,
            "ruta_archivo": self.ruta_archivo,
            "total_datos_entrenamiento": self.total_datos_entrenamiento,
            "total_datos_test": self.total_datos_test,
            "test_size": self.test_size,
            "random_state": self.random_state,
            "activo": self.activo,
            "descripcion": self.descripcion,
            "features_usadas": self.features_usadas.split(",") if self.features_usadas else [],
            "usuario_id": self.usuario_id,
            "entrenado_en": self.entrenado_en.isoformat() if self.entrenado_en else None,
            "activado_en": self.activado_en.isoformat() if self.activado_en else None,
        }
