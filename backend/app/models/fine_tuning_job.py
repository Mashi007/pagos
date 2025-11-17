"""
Modelo de Fine-tuning Job
Almacena jobs de entrenamiento de fine-tuning
"""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class FineTuningJob(Base):
    """
    Job de fine-tuning de OpenAI
    """

    __tablename__ = "fine_tuning_jobs"

    id = Column(Integer, primary_key=True, index=True)

    # ID del job en OpenAI
    openai_job_id = Column(String(100), unique=True, nullable=False, index=True)

    # Estado del job
    status = Column(
        String(50), nullable=False, default="pending", index=True
    )  # pending, running, succeeded, failed, cancelled

    # Información del modelo
    modelo_base = Column(
        String(100), nullable=False
    )  # gpt-4o, gpt-4o-2024-08-06, etc. (gpt-4o-mini no disponible para fine-tuning)
    modelo_entrenado = Column(String(200), nullable=True)  # ID del modelo entrenado en OpenAI

    # Archivo de entrenamiento
    archivo_entrenamiento = Column(String(500), nullable=True)  # ID del archivo en OpenAI
    total_conversaciones = Column(Integer, nullable=True)

    # Progreso
    progreso = Column(Float, nullable=True)  # 0.0 - 100.0

    # Errores
    error = Column(Text, nullable=True)

    # Metadatos adicionales
    epochs = Column(Integer, nullable=True)
    learning_rate = Column(Float, nullable=True)

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    completado_en = Column(DateTime, nullable=True)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<FineTuningJob {self.openai_job_id} - {self.status}>"

    def to_dict(self):
        """Convierte el job a diccionario"""
        return {
            "id": self.openai_job_id,  # Usar openai_job_id como ID principal para compatibilidad con frontend
            "status": self.status,
            "modelo_base": self.modelo_base,
            "modelo_entrenado": self.modelo_entrenado,
            "archivo_entrenamiento": self.archivo_entrenamiento,
            "total_conversaciones": self.total_conversaciones,
            "progreso": self.progreso,
            "error": self.error,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "completado_en": self.completado_en.isoformat() if self.completado_en else None,
        }
