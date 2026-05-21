"""Casos de cobranza (gestion de mora, acuerdos, evidencia fotografica)."""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class CobranzaCaso(Base):
    __tablename__ = "cobranza_casos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prestamo_id = Column(
        Integer, ForeignKey("prestamos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cliente_id = Column(
        Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cedula = Column(String(20), nullable=False, index=True)
    nombres = Column(String(255), nullable=True)
    motivo = Column(String(40), nullable=False, server_default=text("'OTRO'"))
    estado = Column(String(20), nullable=False, server_default=text("'ABIERTO'"))
    observaciones = Column(Text, nullable=True)
    monto_financiamiento = Column(Numeric(14, 2), nullable=True)
    saldo_pendiente_snapshot = Column(Numeric(14, 2), nullable=True)
    cuotas_atrasadas_snapshot = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    creado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    actualizado_en = Column(
        DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CobranzaImagen(Base):
    __tablename__ = "cobranza_imagenes"

    id = Column(String(32), primary_key=True)
    caso_id = Column(
        Integer,
        ForeignKey("cobranza_casos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_type = Column(String(80), nullable=False)
    imagen_data = Column(LargeBinary, nullable=False)
    descripcion = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())


class CobranzaAcuerdo(Base):
    __tablename__ = "cobranza_acuerdos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    caso_id = Column(
        Integer,
        ForeignKey("cobranza_casos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fecha_acuerdo = Column(Date, nullable=False)
    fecha_compromiso = Column(Date, nullable=True)
    notas = Column(Text, nullable=False)
    estado = Column(String(20), nullable=False, server_default=text("'PENDIENTE'"))
    monto_compromiso = Column(Numeric(14, 2), nullable=True)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    creado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    actualizado_en = Column(
        DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now()
    )
