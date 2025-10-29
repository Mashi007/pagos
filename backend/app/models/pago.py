from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.db.session import Base

CEDULA_LENGTH = 20
DOCUMENTO_LENGTH = 100
DOCUMENTO_NOMBRE_LENGTH = 255
DOCUMENTO_TIPO_LENGTH = 10
DOCUMENTO_RUTA_LENGTH = 500
NUMERIC_PRECISION = 12
NUMERIC_SCALE = 2


class Pago(Base):
    """
    Modelo para pagos
    Representa los pagos realizados por los clientes
    """

    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)

    # DATOS DEL CLIENTE
    cedula_cliente = Column(String(CEDULA_LENGTH), nullable=False, index=True)

    # DATOS DEL PAGO
    prestamo_id = Column(Integer, nullable=True, index=True)  # ID del crédito
    fecha_pago = Column(DateTime, nullable=False)  # Fecha de pago (manual)
    fecha_registro = Column(
        DateTime, default=func.now(), nullable=False
    )  # Fecha de registro (automático)
    monto_pagado = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    numero_documento = Column(String(DOCUMENTO_LENGTH), nullable=False, index=True)
    institucion_bancaria = Column(String(100), nullable=True)  # Institución bancaria

    # DOCUMENTO ADJUNTO
    documento_nombre = Column(String(DOCUMENTO_NOMBRE_LENGTH), nullable=True)
    documento_tipo = Column(
        String(DOCUMENTO_TIPO_LENGTH), nullable=True
    )  # PNG, JPG, PDF
    documento_tamaño = Column(Integer, nullable=True)  # bytes
    documento_ruta = Column(String(DOCUMENTO_RUTA_LENGTH), nullable=True)

    # ESTADO DE CONCILIACIÓN
    conciliado = Column(Boolean, default=False, nullable=False)
    fecha_conciliacion = Column(DateTime, nullable=True)

    # ESTADO DEL PAGO
    estado = Column(
        String(20), default="PAGADO", nullable=False, index=True
    )  # PENDIENTE, PAGADO, PARCIAL, ADELANTADO

    # CONTROL Y AUDITORÍA
    activo = Column(Boolean, default=True, nullable=False)
    notas = Column(Text, nullable=True)
    usuario_registro = Column(
        String(100), nullable=False
    )  # Email del usuario que registró el pago
    fecha_actualizacion = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)

    def __repr__(self):
        return f"<Pago(id={self.id}, cedula={self.cedula_cliente}, monto={self.monto_pagado}, conciliado={self.conciliado})>"
