"""
Modelo para tabla pagos_con_errores: pagos con errores de validación desde Carga Masiva.
No se mezclan con pagos que cumplen validadores. Vista Revisar Pagos.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func, text

from app.core.database import Base


class PagoConError(Base):
    __tablename__ = "pagos_con_errores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id", ondelete="SET NULL"), nullable=True, index=True)
    cedula_cliente = Column("cedula", String(20), nullable=True, index=True)
    fecha_pago = Column(DateTime(timezone=False), nullable=False)
    monto_pagado = Column(Numeric(14, 2), nullable=False)
    numero_documento = Column(String(100), nullable=True)
    institucion_bancaria = Column(String(255), nullable=True)
    estado = Column(String(30), nullable=True)
    fecha_registro = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_conciliacion = Column(DateTime(timezone=False), nullable=True)
    conciliado = Column(Boolean, nullable=True)
    verificado_concordancia = Column(String(10), nullable=False, server_default=text("''"))
    usuario_registro = Column(String(255), nullable=True)
    notas = Column(Text, nullable=True)
    documento_nombre = Column(String(255), nullable=True)
    documento_tipo = Column(String(50), nullable=True)
    documento_ruta = Column(String(255), nullable=True)
    referencia_pago = Column(String(100), nullable=False, server_default=text("''"))
    errores_descripcion = Column(JSONB, nullable=True)
    observaciones = Column(String(255), nullable=True)  # Nombres de campos con problema, separados por coma
    fila_origen = Column(Integer, nullable=True)
