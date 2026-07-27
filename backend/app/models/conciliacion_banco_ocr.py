"""Modelos SQLAlchemy para Conciliacion Bancos (Auditoria)."""
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


class ConciliacionBancoOcrLote(Base):
    __tablename__ = "conciliacion_banco_ocr_lote"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, nullable=True)
    archivo_nombre = Column(String(255), nullable=False)
    fecha_desde = Column(Date, nullable=False)
    fecha_hasta = Column(Date, nullable=False)
    estado = Column(String(30), nullable=False, server_default=text("'CARGADO'"))
    moneda_carga = Column(String(3), nullable=False, server_default=text("'USD'"))
    notas = Column(Text, nullable=True)
    creado_en = Column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )


class ConciliacionBancoOcrBanco(Base):
    __tablename__ = "conciliacion_banco_ocr_banco"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lote_id = Column(
        Integer,
        ForeignKey("conciliacion_banco_ocr_lote.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fila_excel = Column(Integer, nullable=False)
    fecha_banco = Column(Date, nullable=True)
    referencia_banco = Column(Text, nullable=False)
    ref_banco_norm = Column(Text, nullable=True, index=True)
    monto_banco = Column(Numeric(14, 2), nullable=True)
    monto_banco_original = Column(Numeric(14, 2), nullable=True)
    moneda_fila = Column(String(3), nullable=True)


class ConciliacionBancoOcrResultado(Base):
    __tablename__ = "conciliacion_banco_ocr_resultado"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lote_id = Column(
        Integer,
        ForeignKey("conciliacion_banco_ocr_lote.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    banco_id = Column(
        Integer,
        ForeignKey("conciliacion_banco_ocr_banco.id", ondelete="SET NULL"),
        nullable=True,
    )
    pago_id = Column(
        Integer,
        ForeignKey("pagos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fecha_banco = Column(Date, nullable=True)
    fecha_bd = Column(Date, nullable=True)
    referencia_banco = Column(Text, nullable=True)
    referencia_bd = Column(Text, nullable=True)
    monto_banco = Column(Numeric(14, 2), nullable=True)
    monto_bd = Column(Numeric(14, 2), nullable=True)
    similitud_pct = Column(Numeric(5, 2), nullable=True)
    tipo_novedad = Column(String(40), nullable=False)
    decision = Column(
        String(20), nullable=False, server_default=text("'PENDIENTE'")
    )
    fuente_elegida = Column(String(10), nullable=True)
    aplicado = Column(Boolean, nullable=False, server_default=text("false"))
    detalle_aplicacion = Column(Text, nullable=True)
    usuario_decision_id = Column(Integer, nullable=True)
    decidido_en = Column(DateTime(timezone=False), nullable=True)
    valores_antes = Column(Text, nullable=True)
    valores_despues = Column(Text, nullable=True)
    creado_en = Column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )


class ConciliacionBancoExtracto(Base):
    """Extracto bancario persistente (Banco/Fecha/Referencia/Monto) para re-conciliar."""

    __tablename__ = "conciliacion_banco_extracto"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    banco = Column(String(40), nullable=False, index=True)
    fecha = Column(Date, nullable=True, index=True)
    referencia = Column(Text, nullable=False)
    referencia_norm = Column(Text, nullable=True, index=True)
    monto = Column(Numeric(14, 2), nullable=True)
    moneda = Column(String(3), nullable=False, server_default=text("'USD'"))
    clave_natural = Column(Text, nullable=False, unique=True)
    lote_origen_id = Column(
        Integer,
        ForeignKey("conciliacion_banco_ocr_lote.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    archivo_nombre = Column(String(255), nullable=True)
    creado_en = Column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    actualizado_en = Column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )

