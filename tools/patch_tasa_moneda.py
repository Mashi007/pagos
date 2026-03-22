"""One-off patch script: tasa por fecha_pago, Caracas, pagos BS conversion."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TASA_PATH = ROOT / "backend" / "app" / "services" / "tasa_cambio_service.py"
TASA_NEW = '''"""
Servicios para gestionar tasas de cambio oficiales.
"""
from datetime import date, datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tasa_cambio_diaria import TasaCambioDiaria

# Fecha contable y hora de negocio en America/Caracas (tasas diarias, validaciones).
CARACAS_TZ = ZoneInfo("America/Caracas")


def fecha_hoy_caracas() -> date:
    """Fecha calendario actual en Caracas (para tasa del dia y validaciones)."""
    return datetime.now(CARACAS_TZ).date()


def ahora_caracas() -> datetime:
    """DateTime con zona America/Caracas."""
    return datetime.now(CARACAS_TZ)


def obtener_tasa_hoy(db: Session) -> Optional[TasaCambioDiaria]:
    """Obtiene la tasa de cambio oficial para hoy (calendario Caracas)."""
    hoy = fecha_hoy_caracas()
    return db.execute(
        select(TasaCambioDiaria).where(TasaCambioDiaria.fecha == hoy)
    ).scalars().first()


def obtener_tasa_por_fecha(db: Session, fecha: date) -> Optional[TasaCambioDiaria]:
    """Obtiene la tasa oficial para una fecha (fecha de pago = clave en tasas_cambio_diaria)."""
    return db.execute(
        select(TasaCambioDiaria).where(TasaCambioDiaria.fecha == fecha)
    ).scalars().first()


def guardar_tasa_diaria(
    db: Session,
    tasa_oficial: float,
    usuario_id: Optional[int] = None,
    usuario_email: Optional[str] = None,
) -> TasaCambioDiaria:
    """Guarda o actualiza la tasa de cambio para hoy (calendario Caracas)."""
    hoy = fecha_hoy_caracas()
    existente = db.execute(
        select(TasaCambioDiaria).where(TasaCambioDiaria.fecha == hoy)
    ).scalars().first()

    if existente:
        existente.tasa_oficial = tasa_oficial
        existente.usuario_id = usuario_id
        existente.usuario_email = usuario_email
        existente.updated_at = datetime.now()
    else:
        existente = TasaCambioDiaria(
            fecha=hoy,
            tasa_oficial=tasa_oficial,
            usuario_id=usuario_id,
            usuario_email=usuario_email,
        )
        db.add(existente)

    db.commit()
    db.refresh(existente)
    return existente


def convertir_bs_a_usd(monto_bs: float, tasa: float) -> float:
    """Convierte Bolivares a Dolares usando la tasa oficial (Bs por 1 USD)."""
    if tasa <= 0:
        raise ValueError("La tasa de cambio debe ser mayor a 0")
    return round(monto_bs / tasa, 2)


def debe_ingresar_tasa() -> bool:
    """True desde las 01:00 hora Caracas (ventana de ingreso diario)."""
    ahora = ahora_caracas().time()
    inicio = time(1, 0)
    return ahora >= inicio
'''

PAGO_MODEL_PATH = ROOT / "backend" / "app" / "models" / "pago.py"
PAGO_MODEL_NEW = '''"""
Modelo SQLAlchemy para registro de pagos (tabla pagos).
Conectado al frontend /pagos/pagos; lista y CRUD desde BD.
Columnas alineadas con la tabla real en Render (cedula, fecha_pago timestamp, referencia_pago, etc.).
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Boolean, ForeignKey, Date
from sqlalchemy.sql import func, text

from app.core.database import Base


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id", ondelete="SET NULL"), nullable=True, index=True)
    # BD tiene columna "cedula"; en Python/API se expone como cedula_cliente
    cedula_cliente = Column("cedula", String(20), nullable=True, index=True)
    fecha_pago = Column(DateTime(timezone=False), nullable=False)
    # Monto en USD para cartera/cuotas (si el reporte fue en Bs, se convierte con tasa del dia de fecha_pago).
    monto_pagado = Column(Numeric(14, 2), nullable=False)
    numero_documento = Column(String(100), nullable=True, unique=True)  # Regla general: no duplicados en documentos
    institucion_bancaria = Column(String(255), nullable=True)
    estado = Column(String(30), nullable=True)
    fecha_registro = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_conciliacion = Column(DateTime(timezone=False), nullable=True)
    conciliado = Column(Boolean, nullable=False, server_default=text("false"))  # [B2] Siempre boolean, no nullable
    verificado_concordancia = Column(String(10), nullable=False, server_default=text("''"))
    usuario_registro = Column(String(255), nullable=True)
    notas = Column(Text, nullable=True)
    documento_nombre = Column(String(255), nullable=True)
    documento_tipo = Column(String(50), nullable=True)
    documento_ruta = Column(String(255), nullable=True)
    # NOT NULL en BD; obligatorio al insertar
    referencia_pago = Column(String(100), nullable=False, server_default=text("''"))
    # Auditoria moneda (solo datos en BD; monto_pagado siempre USD cuando aplica conversion)
    moneda_registro = Column(String(10), nullable=True)  # USD | BS
    monto_bs_original = Column(Numeric(15, 2), nullable=True)
    tasa_cambio_bs_usd = Column(Numeric(15, 6), nullable=True)
    fecha_tasa_referencia = Column(Date, nullable=True)  # misma fecha de pago usada para buscar tasa
'''


def main() -> None:
    TASA_PATH.write_text(TASA_NEW, encoding="utf-8")
    PAGO_MODEL_PATH.write_text(PAGO_MODEL_NEW, encoding="utf-8")
    print("Wrote", TASA_PATH)
    print("Wrote", PAGO_MODEL_PATH)


if __name__ == "__main__":
    main()
