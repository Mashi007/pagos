"""
Modelo SQLAlchemy para registro de pagos (tabla pagos).
Conectado al frontend /pagos/pagos; lista y CRUD desde BD.
"""
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func, text

from app.core.database import Base


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula_cliente = Column(String(20), nullable=False, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id", ondelete="SET NULL"), nullable=True, index=True)
    fecha_pago = Column(Date, nullable=False)
    monto_pagado = Column(Numeric(14, 2), nullable=False)
    numero_documento = Column(String(100), nullable=False)
    institucion_bancaria = Column(String(255), nullable=True)
    estado = Column(String(30), nullable=False, default="PENDIENTE", index=True)
    fecha_registro = Column(DateTime(timezone=False), nullable=True, server_default=func.now())
    fecha_conciliacion = Column(DateTime(timezone=False), nullable=True)
    conciliado = Column(Boolean, nullable=False, server_default=text("false"))
    verificado_concordancia = Column(String(10), nullable=True)  # SI/NO
    usuario_registro = Column(String(255), nullable=True, server_default=text("''"))
    notas = Column(Text, nullable=True)
    documento_nombre = Column(String(255), nullable=True)
    documento_tipo = Column(String(50), nullable=True)
    documento_ruta = Column(Text, nullable=True)
