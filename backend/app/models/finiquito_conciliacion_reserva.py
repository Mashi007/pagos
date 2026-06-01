"""Reserva temporal de comprobantes/pagos para conciliacion Visto (finiquito area revision)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    Index,
)
from sqlalchemy.sql import func

from app.core.database import Base


class FiniquitoConciliacionReserva(Base):
    """
    Snapshot de pagos con comprobante antes de borrar pagos del prestamo.
    Incluye bytes del comprobante para re-OCR sin volver a Drive/BD externa.
    Se elimina al pasar el caso a EN_PROCESO (Visto final o X).
    """

    __tablename__ = "finiquito_conciliacion_reserva"

    id = Column(Integer, primary_key=True, autoincrement=True)
    caso_id = Column(
        Integer,
        ForeignKey("finiquito_casos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prestamo_id = Column(
        Integer,
        ForeignKey("prestamos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    orden = Column(Integer, nullable=False, default=0)

    pago_id_origen = Column(Integer, nullable=True)
    cedula_cliente = Column(String(20), nullable=True)
    monto_pagado = Column(Numeric(14, 2), nullable=False)
    fecha_pago = Column(DateTime(timezone=False), nullable=False)
    numero_documento = Column(String(100), nullable=True)
    referencia_pago = Column(String(100), nullable=False, server_default="")
    institucion_bancaria = Column(String(255), nullable=True)
    link_comprobante = Column(Text, nullable=True)
    documento_ruta = Column(String(255), nullable=True)
    comprobante_imagen_data = Column(LargeBinary, nullable=True)
    comprobante_content_type = Column(String(80), nullable=True)
    comprobante_nombre_archivo = Column(String(255), nullable=True)
    moneda_registro = Column(String(10), nullable=True)
    monto_bs_original = Column(Numeric(15, 2), nullable=True)
    tasa_cambio_bs_usd = Column(Numeric(15, 6), nullable=True)
    conciliado = Column(Boolean, nullable=False, server_default="false")
    notas = Column(Text, nullable=True)

    pago_id_recriado = Column(Integer, nullable=True, index=True)
    ocr_ok = Column(Boolean, nullable=True)
    ocr_error = Column(Text, nullable=True)
    ocr_sugerencia_json = Column(Text, nullable=True)

    creado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_finiquito_conc_reserva_caso_orden", "caso_id", "orden"),
    )
