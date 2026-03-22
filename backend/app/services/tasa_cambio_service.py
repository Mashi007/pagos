"""
Servicios para gestionar tasas de cambio oficiales.
"""
from datetime import date, datetime, time
from typing import Optional, Tuple
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


def guardar_tasa_para_fecha(
    db: Session,
    fecha: date,
    tasa_oficial: float,
    usuario_id: Optional[int] = None,
    usuario_email: Optional[str] = None,
) -> TasaCambioDiaria:
    """
    Inserta o actualiza la tasa oficial para una fecha calendario concreta.
    Usada para backfill (pagos BS con fecha_pago pasada) sin regla de hora 01:00.
    """
    if tasa_oficial <= 0:
        raise ValueError("La tasa de cambio debe ser mayor a 0")

    existente = db.execute(
        select(TasaCambioDiaria).where(TasaCambioDiaria.fecha == fecha)
    ).scalars().first()

    if existente:
        existente.tasa_oficial = tasa_oficial
        existente.usuario_id = usuario_id
        existente.usuario_email = usuario_email
        existente.updated_at = datetime.now()
    else:
        existente = TasaCambioDiaria(
            fecha=fecha,
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


def tasa_y_equivalente_usd_excel(
    db: Session,
    fecha_pago: date,
    monto: float,
    moneda: Optional[str],
) -> Tuple[Optional[float], Optional[float]]:
    """
    Para exportes (Excel/API): tasa oficial Bs/USD del día fecha_pago y monto en USD.

    - Pago en USD: (None, monto) — no aplica tasa Bs; el monto ya es dólares.
    - Pago en Bs: (tasa_oficial, monto_bs/tasa) si existe tasa para fecha_pago; si no, (None, None).
    """
    raw = (moneda or "BS").strip().upper()
    if raw in (
        "USD",
        "US$",
        "$",
        "DOLAR",
        "DÓLAR",
        "DOLARES",
        "DÓLARES",
    ):
        return None, round(float(monto), 2)
    tasa_row = obtener_tasa_por_fecha(db, fecha_pago)
    if tasa_row is None:
        return None, None
    t = float(tasa_row.tasa_oficial)
    return t, convertir_bs_a_usd(float(monto), t)


def debe_ingresar_tasa() -> bool:
    """True desde las 01:00 hora Caracas (ventana de ingreso diario)."""
    ahora = ahora_caracas().time()
    inicio = time(1, 0)
    return ahora >= inicio
