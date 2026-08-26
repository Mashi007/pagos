# -*- coding: utf-8 -*-
"""Modelos: Importación extracto (faltantes) — Auditoría."""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func, text

from app.core.database import Base


class ImportacionExtractoLote(Base):
    __tablename__ = "importacion_extracto_lote"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, nullable=True)
    archivo_nombre = Column(String(255), nullable=False)
    estado = Column(String(30), nullable=False, server_default=text("'COMPARADO'"))
    notas = Column(Text, nullable=True)
    # Banco del extracto (Mercantil, BNC, Binance, Zelle, BNV) — todo el lote comparte este valor.
    banco = Column(String(50), nullable=True, index=True)
    creado_en = Column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )


class ImportacionExtractoFila(Base):
    __tablename__ = "importacion_extracto_fila"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lote_id = Column(
        Integer,
        ForeignKey("importacion_extracto_lote.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fila_excel = Column(Integer, nullable=False)
    fecha_deposito = Column(Date, nullable=True)
    descripcion_raw = Column(Text, nullable=True)
    cedula = Column(String(32), nullable=True, index=True)
    serial = Column(String(100), nullable=True, index=True)
    serial_norm = Column(String(100), nullable=True, index=True)
    monto_usd = Column(Numeric(14, 2), nullable=True)
    # IGUAL_100 | SE_PUEDE_IMPORTAR | SEMEJANTE | PARSE_ERROR | SIN_PRESTAMO |
    # VARIOS_PRESTAMOS | VISTO | IMPORTADO
    estado = Column(String(40), nullable=False, server_default=text("'PARSE_ERROR'"))
    similitud_pct = Column(Numeric(5, 2), nullable=True)
    pago_id_match = Column(Integer, nullable=True)
    prestamo_id = Column(Integer, nullable=True)
    pago_id_creado = Column(Integer, nullable=True)
    detalle = Column(Text, nullable=True)
    visto = Column(Boolean, nullable=False, server_default=text("false"))
    importado = Column(Boolean, nullable=False, server_default=text("false"))
    oculto = Column(Boolean, nullable=False, server_default=text("false"))
