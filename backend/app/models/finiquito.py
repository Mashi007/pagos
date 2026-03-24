"""Modelos Finiquito: acceso OTP publico, casos materializados, historial de estados."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class FiniquitoUsuarioAcceso(Base):
    """Usuario del portal Finiquito (cedula + email unicos; login por codigo al correo)."""

    __tablename__ = "finiquito_usuario_acceso"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cedula = Column(String(20), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    creado_en = Column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )


class FiniquitoLoginCodigo(Base):
    """Codigo de un solo uso enviado al email (login Finiquito)."""

    __tablename__ = "finiquito_login_codigos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    finiquito_usuario_id = Column(
        Integer,
        ForeignKey("finiquito_usuario_acceso.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo = Column(String(10), nullable=False)
    expira_en = Column(DateTime(timezone=False), nullable=False)
    usado = Column(Boolean, nullable=False, server_default=text("false"))
    creado_en = Column(DateTime(timezone=False), nullable=False)


class FiniquitoCaso(Base):
    """
    Caso listo para proceso de finiquito: total_financiamiento = sum(cuotas.total_pagado)
    (comparacion exacta). Rellenado por job 02:00 America/Caracas.
    """

    __tablename__ = "finiquito_casos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prestamo_id = Column(
        Integer,
        ForeignKey("prestamos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    cliente_id = Column(
        Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cedula = Column(String(20), nullable=False, index=True)
    total_financiamiento = Column(Numeric(14, 2), nullable=False)
    sum_total_pagado = Column(Numeric(14, 2), nullable=False)
    estado = Column(String(20), nullable=False, server_default=text("'REVISION'"))
    ultimo_refresh_utc = Column(DateTime(timezone=False), nullable=True)
    creado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    actualizado_en = Column(
        DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class FiniquitoEstadoHistorial(Base):
    """Auditoria: usuario/fecha de cada cambio de estado."""

    __tablename__ = "finiquito_estado_historial"

    id = Column(Integer, primary_key=True, autoincrement=True)
    caso_id = Column(
        Integer,
        ForeignKey("finiquito_casos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    estado_anterior = Column(String(20), nullable=True)
    estado_nuevo = Column(String(20), nullable=False)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    finiquito_usuario_id = Column(
        Integer,
        ForeignKey("finiquito_usuario_acceso.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_tipo = Column(String(20), nullable=False)
    creado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
