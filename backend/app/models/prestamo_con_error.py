"""
Modelo SQLAlchemy para préstamos con errores de validación (carga masiva).
Similar a PagoConError y ClienteConError.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, text, Numeric

from app.core.database import Base


class PrestamoConError(Base):
    __tablename__ = "prestamos_con_errores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula_cliente = Column(String(20), nullable=True, index=True)
    total_financiamiento = Column(Numeric(14, 2), nullable=True)
    modalidad_pago = Column(String(50), nullable=True)
    numero_cuotas = Column(Integer, nullable=True)
    producto = Column(String(255), nullable=True)
    analista = Column(String(255), nullable=True)
    concesionario = Column(String(255), nullable=True)
    estado = Column(String(30), nullable=True, server_default=text("'PENDIENTE'"))
    errores_descripcion = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)
    fila_origen = Column(Integer, nullable=True)
    fecha_registro = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    usuario_registro = Column(String(255), nullable=True)
