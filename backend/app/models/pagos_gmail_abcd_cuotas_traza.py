# -*- coding: utf-8 -*-
"""
Trazabilidad Gmail (Gemini, plantilla A–D) → alta en `pagos` → aplicación a cuotas.

Cada fila describe el resultado por comprobante / ítem sync tras el escaneo.
Ver `etapa_final` para saber si el dinero llegó a cuotas (`CUOTAS_OK` vs otros códigos).
"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.sql import func, text

from app.core.database import Base


class PagosGmailAbcdCuotasTraza(Base):
    __tablename__ = "pagos_gmail_abcd_cuotas_traza"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sync_id = Column(
        Integer,
        ForeignKey("pagos_gmail_sync.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sync_item_id = Column(
        Integer,
        ForeignKey("pagos_gmail_sync_item.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    plantilla_fmt = Column(String(4), nullable=False)
    cedula = Column(String(50), nullable=True)
    numero_referencia = Column(String(200), nullable=True)
    banco_excel = Column(String(50), nullable=True)
    archivo_adjunto = Column(String(500), nullable=True)
    comprobante_imagen_id = Column(String(32), nullable=True)

    duplicado_documento = Column(Boolean, nullable=False, server_default=text("false"))
    # CUOTAS_OK | PAGO_SIN_CUOTAS | OMITIDO_DUPLICADO | OMITIDO_NEGOCIO | ERROR_PIPELINE
    etapa_final = Column(String(40), nullable=False, index=True)
    motivo = Column(String(80), nullable=True)
    detalle = Column(Text, nullable=True)

    pago_id = Column(
        Integer,
        ForeignKey("pagos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prestamo_id = Column(
        Integer,
        ForeignKey("prestamos.id", ondelete="SET NULL"),
        nullable=True,
    )
    cuotas_completadas = Column(Integer, nullable=False, server_default="0")
    cuotas_parciales = Column(Integer, nullable=False, server_default="0")
    conciliado_final = Column(Boolean, nullable=True)
    pago_estado_final = Column(String(30), nullable=True)

    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
