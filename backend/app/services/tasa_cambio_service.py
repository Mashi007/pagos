"""
Servicios para gestionar tasas de cambio oficiales.
"""
from datetime import date, datetime, time
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.tasa_cambio_diaria import TasaCambioDiaria


def obtener_tasa_hoy(db: Session) -> Optional[TasaCambioDiaria]:
    """Obtiene la tasa de cambio oficial para hoy."""
    hoy = date.today()
    return db.execute(
        select(TasaCambioDiaria).where(TasaCambioDiaria.fecha == hoy)
    ).scalars().first()


def obtener_tasa_por_fecha(db: Session, fecha: date) -> Optional[TasaCambioDiaria]:
    """Obtiene la tasa de cambio oficial para una fecha específica."""
    return db.execute(
        select(TasaCambioDiaria).where(TasaCambioDiaria.fecha == fecha)
    ).scalars().first()


def guardar_tasa_diaria(db: Session, tasa_oficial: float, usuario_id: Optional[int] = None, usuario_email: Optional[str] = None) -> TasaCambioDiaria:
    """Guarda o actualiza la tasa de cambio para hoy."""
    hoy = date.today()
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
    """Convierte Bolívares a Dólares usando la tasa oficial."""
    if tasa <= 0:
        raise ValueError("La tasa de cambio debe ser mayor a 0")
    return round(monto_bs / tasa, 2)


def debe_ingresar_tasa() -> bool:
    """Verifica si se debe solicitar el ingreso de la tasa (desde las 01:00 AM)."""
    ahora = datetime.now().time()
    inicio = time(1, 0)  # 01:00 AM
    # Retorna True si estamos entre 01:00 AM y 23:59 PM
    return ahora >= inicio
