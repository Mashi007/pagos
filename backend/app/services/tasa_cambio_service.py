"""
Servicios para gestionar tasas de cambio oficiales.
"""
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.tasa_cambio_diaria import TasaCambioDiaria

# Limite superior defensivo (evita errores de tipeo masivos). Ajustar si el BCV supera este orden.
_TASA_OFICIAL_MAX_GUARDADO = Decimal("999999999.999999")

# Valor usado en scripts de ejemplo; rechazar en API para no persistir datos ficticios.
_TASA_PLACEHOLDER_EJEMPLO_MIN = Decimal("99999.97")
_TASA_PLACEHOLDER_EJEMPLO_MAX = Decimal("100000.01")

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


def es_tasa_problematica_para_operacion(tasa_oficial: Any) -> bool:
    """True si la tasa no debe usarse en conversiones (cero, negativa o placeholder de ejemplo)."""
    try:
        x = Decimal(str(tasa_oficial))
    except Exception:
        return True
    if x <= 0:
        return True
    return _TASA_PLACEHOLDER_EJEMPLO_MIN <= x <= _TASA_PLACEHOLDER_EJEMPLO_MAX


def validar_tasa_oficial_antes_de_guardar(tasa_oficial: float) -> None:
    """
    Reglas al persistir tasa BCV (API y servicio).
    Rechaza cero, negativos, valores absurdamente altos y el placeholder 99999.99 de plantillas SQL.
    """
    try:
        x = Decimal(str(tasa_oficial))
    except Exception as e:
        raise ValueError("La tasa de cambio no es un numero valido") from e
    if x <= 0:
        raise ValueError("La tasa de cambio debe ser mayor a 0")
    if x > _TASA_OFICIAL_MAX_GUARDADO:
        raise ValueError(
            f"La tasa supera el maximo permitido ({_TASA_OFICIAL_MAX_GUARDADO}). "
            "Revise el valor (posible error de tipeo)."
        )
    if _TASA_PLACEHOLDER_EJEMPLO_MIN <= x <= _TASA_PLACEHOLDER_EJEMPLO_MAX:
        raise ValueError(
            "Valor rechazado: coincide con la tasa de ejemplo de plantillas (99999.99). "
            "Ingrese la tasa BCV oficial real del dia."
        )


def listar_tasas_problematicas(db: Session) -> List[TasaCambioDiaria]:
    """Filas con tasa <= 0 o en el rango placeholder 99999.97–100000.01."""
    rows = (
        db.execute(
            select(TasaCambioDiaria)
            .where(
                or_(
                    TasaCambioDiaria.tasa_oficial <= 0,
                    TasaCambioDiaria.tasa_oficial.between(
                        _TASA_PLACEHOLDER_EJEMPLO_MIN, _TASA_PLACEHOLDER_EJEMPLO_MAX
                    ),
                )
            )
            .order_by(TasaCambioDiaria.fecha.asc())
        )
        .scalars()
        .all()
    )
    return list(rows)


def _tasa_vecina_valida(db: Session, fecha_objetivo: date) -> Optional[Decimal]:
    """Tasa de la fila valida mas cercana (fecha anterior, si no la siguiente)."""
    anteriores = (
        db.execute(
            select(TasaCambioDiaria)
            .where(TasaCambioDiaria.fecha < fecha_objetivo)
            .order_by(TasaCambioDiaria.fecha.desc())
        )
        .scalars()
        .all()
    )
    for r in anteriores:
        if not es_tasa_problematica_para_operacion(r.tasa_oficial):
            return Decimal(str(r.tasa_oficial))
    posteriores = (
        db.execute(
            select(TasaCambioDiaria)
            .where(TasaCambioDiaria.fecha > fecha_objetivo)
            .order_by(TasaCambioDiaria.fecha.asc())
        )
        .scalars()
        .all()
    )
    for r in posteriores:
        if not es_tasa_problematica_para_operacion(r.tasa_oficial):
            return Decimal(str(r.tasa_oficial))
    return None


def rellenar_tasas_problematicas_desde_vecino(
    db: Session,
    *,
    dry_run: bool,
    usuario_email: str,
) -> dict[str, Any]:
    """
    Para cada fila problematica en tasas_cambio_diaria, propone o aplica la tasa de la fecha
    valida mas cercana (misma idea que el SQL operativo de backfill).

    No sustituye al dato BCV oficial: conviene revisar despues contra la fuente BCV.
    """
    malas = listar_tasas_problematicas(db)
    cambios: list[dict[str, Any]] = []
    for row in malas:
        propuesta = _tasa_vecina_valida(db, row.fecha)
        cambios.append(
            {
                "fecha": row.fecha.isoformat(),
                "tasa_anterior": float(row.tasa_oficial) if row.tasa_oficial is not None else None,
                "tasa_propuesta": float(propuesta) if propuesta is not None else None,
                "aplicable": propuesta is not None,
            }
        )
        if not dry_run and propuesta is not None:
            row.tasa_oficial = propuesta
            row.usuario_email = usuario_email
            row.updated_at = datetime.now()
    aplicables = sum(1 for c in cambios if c.get("aplicable"))
    if not dry_run and aplicables:
        db.commit()
    return {
        "dry_run": dry_run,
        "filas_problematicas": len(malas),
        "filas_con_propuesta": aplicables,
        "cambios": cambios,
    }


def obtener_tasa_por_fecha(db: Session, fecha: date) -> Optional[TasaCambioDiaria]:
    """Obtiene la tasa oficial para una fecha (fecha de pago = clave en tasas_cambio_diaria)."""
    return db.execute(
        select(TasaCambioDiaria).where(TasaCambioDiaria.fecha == fecha)
    ).scalars().first()


def obtener_tasas_por_fechas(db: Session, fechas: Sequence[date]) -> Dict[date, TasaCambioDiaria]:
    """Una sola consulta para varias fechas (listados / Excel con muchas filas)."""
    uniq = tuple({f for f in fechas if f is not None})
    if not uniq:
        return {}
    rows = db.execute(
        select(TasaCambioDiaria).where(TasaCambioDiaria.fecha.in_(uniq))
    ).scalars().all()
    return {r.fecha: r for r in rows}


def guardar_tasa_diaria(
    db: Session,
    tasa_oficial: float,
    usuario_id: Optional[int] = None,
    usuario_email: Optional[str] = None,
) -> TasaCambioDiaria:
    """Guarda o actualiza la tasa de cambio para hoy (calendario Caracas)."""
    validar_tasa_oficial_antes_de_guardar(tasa_oficial)
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
    validar_tasa_oficial_antes_de_guardar(tasa_oficial)

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
    tasas_por_fecha: Optional[Dict[date, Optional[TasaCambioDiaria]]] = None,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Para exportes (Excel/API): tasa oficial Bs/USD del día fecha_pago y monto en USD.

    - Pago en USD: (None, monto) — no aplica tasa Bs; el monto ya es dólares.
    - Pago en Bs: (tasa_oficial, monto_bs/tasa) si existe tasa para fecha_pago; si no, (None, None).

    Si se pasa tasas_por_fecha (prefetch con obtener_tasas_por_fechas), no se consulta BD por fila.
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
    if tasas_por_fecha is not None:
        tasa_row = tasas_por_fecha.get(fecha_pago)
    else:
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
