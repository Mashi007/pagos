"""Reserva temporal de comprobantes para conciliación de cartera en revisión manual (solo admin)."""

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


class RevisionManualConciliacionReserva(Base):
    """
    Snapshot de pagos con comprobante del préstamo en edición antes de borrar pagos.
    Tras OCR y alta en `pagos`, la fila se elimina de esta tabla.
    """

    __tablename__ = "revision_manual_conciliacion_reserva"

    id = Column(Integer, primary_key=True, autoincrement=True)
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
        Index("ix_rev_manual_conc_reserva_prestamo_orden", "prestamo_id", "orden"),
    )
