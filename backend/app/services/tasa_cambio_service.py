"""
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
