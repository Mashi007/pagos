# -*- coding: utf-8 -*-
"""Asignacion fija de prestamos a gestores de cobranza + snapshots diarios."""
from __future__ import annotations

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class CobranzaGestorAsignacion(Base):
    """
    Prestamo APROBADO asignado a un gestor. La fila es inmutable tras el reparto
    inicial (no se rebalancea); los montos del Excel se calculan en vivo.
    """

    __tablename__ = "cobranza_gestor_asignaciones"
    __table_args__ = (
        UniqueConstraint("prestamo_id", name="uq_cobranza_gestor_asignaciones_prestamo"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    prestamo_id = Column(
        Integer,
        ForeignKey("prestamos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gestor_slug = Column(String(64), nullable=False, index=True)
    asignado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CobranzaGestorDesempenoDiario(Base):
    """Snapshot diario (Caracas) del total de cobranza pendiente por gestor."""

    __tablename__ = "cobranza_gestor_desempeno_diario"

    fecha = Column(Date, primary_key=True)
    gestor_slug = Column(String(64), primary_key=True)
    total_cobranza_usd = Column(Numeric(14, 2), nullable=False, server_default="0")
    cantidad_casos = Column(Integer, nullable=False, server_default="0")
    actualizado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
