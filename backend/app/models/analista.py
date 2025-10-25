"""
Modelo de Analista
"""

from sqlalchemy import Boolean, Column, Integer, String

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
            "activo": self.activo
        }