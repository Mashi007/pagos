"""
Modelo SQLAlchemy para clientes con errores de validación (carga masiva).
Similar a PagoConError, para gestionar filas que no se pudieron cargar desde Excel.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, text

from app.core.database import Base


class ClienteConError(Base):
    __tablename__ = "clientes_con_errores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula = Column(String(20), nullable=True, index=True)
    nombres = Column(String(100), nullable=True)
    telefono = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    direccion = Column(Text, nullable=True)
    fecha_nacimiento = Column(String(50), nullable=True)  # String para mantener formato original si es inválida
    ocupacion = Column(String(100), nullable=True)
    estado = Column(String(30), nullable=True, server_default=text("'PENDIENTE'"))
    errores_descripcion = Column(Text, nullable=True)  # JSON o texto de errores
    observaciones = Column(Text, nullable=True)
    fila_origen = Column(Integer, nullable=True)  # Número de fila en Excel para referencia
    fecha_registro = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    usuario_registro = Column(String(255), nullable=True)
