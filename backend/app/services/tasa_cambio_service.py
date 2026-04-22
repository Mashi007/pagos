"""
Servicios para gestionar tasas de cambio oficiales.
"""
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union
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

FuenteTasaCambio = Literal["bcv", "euro", "binance"]


def normalizar_fuente_tasa(raw: Optional[str]) -> FuenteTasaCambio:
    """bcv | euro | binance — defecto euro (comportamiento histórico con `tasa_oficial`)."""
    s = (raw or "").strip().lower()
    if s in ("bcv", "euro", "binance"):
        return s  # type: ignore[return-value]
    return "euro"


def valor_tasa_para_fuente(row: TasaCambioDiaria, fuente: Union[str, FuenteTasaCambio]) -> Optional[float]:
    """
    Devuelve Bs/USD según la fuente elegida en el reporte.
    - euro: columna `tasa_oficial` (Euro / referencia actual del sistema).
    - bcv / binance: columnas dedicadas; None si no hay valor en BD.
    """
    f = normalizar_fuente_tasa(str(fuente))
    if f == "euro":
        try:
            return float(row.tasa_oficial)
        except Exception:
            return None
    if f == "bcv":
        v = getattr(row, "tasa_bcv", None)
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            return None
    v = getattr(row, "tasa_binance", None)
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def mensaje_sin_tasa_para_fuente(fuente: FuenteTasaCambio, fecha_iso: str) -> str:
    if fuente == "bcv":
        return (
            f"No hay tasa BCV registrada para la fecha de pago {fecha_iso}. "
            "Un administrador debe cargarla en Tasas de cambio (BCV) para esa fecha."
        )
    if fuente == "binance":
        return (
            f"No hay tasa Binance registrada para la fecha de pago {fecha_iso}. "
            "Un administrador debe cargarla en Tasas de cambio (Binance) para esa fecha."
        )
    return (
        f"No hay tasa Euro registrada para la fecha de pago {fecha_iso}. "
        "Un administrador debe registrarla en Tasas de cambio para esa fecha."
    )


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
    *,
    tasa_bcv: float,
    tasa_binance: float,
) -> TasaCambioDiaria:
    """
    Guarda o actualiza las tasas del día (calendario Caracas): Euro (`tasa_oficial`), BCV y Binance.
    Misma validación numérica para las tres columnas.
    """
    validar_tasa_oficial_antes_de_guardar(tasa_oficial)
    validar_tasa_oficial_antes_de_guardar(float(tasa_bcv))
    validar_tasa_oficial_antes_de_guardar(float(tasa_binance))
    hoy = fecha_hoy_caracas()
    existente = db.execute(
        select(TasaCambioDiaria).where(TasaCambioDiaria.fecha == hoy)
    ).scalars().first()

    if existente:
        existente.tasa_oficial = tasa_oficial
        existente.tasa_bcv = tasa_bcv
        existente.tasa_binance = tasa_binance
        existente.usuario_id = usuario_id
        existente.usuario_email = usuario_email
        existente.updated_at = datetime.now()
    else:
        existente = TasaCambioDiaria(
            fecha=hoy,
            tasa_oficial=tasa_oficial,
            tasa_bcv=tasa_bcv,
            tasa_binance=tasa_binance,
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
    *,
    tasa_bcv: Optional[float] = None,
    tasa_binance: Optional[float] = None,
) -> TasaCambioDiaria:
    """
    Inserta o actualiza la tasa oficial para una fecha calendario concreta.
    Usada para backfill (pagos BS con fecha_pago pasada) sin regla de hora 01:00.

    `tasa_oficial` es la tasa **Euro** (Bs/USD). `tasa_bcv` y `tasa_binance` son opcionales;
    si vienen en None no se modifican las columnas existentes (solo upsert de euro en fila nueva).
    """
    validar_tasa_oficial_antes_de_guardar(tasa_oficial)
    if tasa_bcv is not None:
        validar_tasa_oficial_antes_de_guardar(float(tasa_bcv))
    if tasa_binance is not None:
        validar_tasa_oficial_antes_de_guardar(float(tasa_binance))

    existente = db.execute(
        select(TasaCambioDiaria).where(TasaCambioDiaria.fecha == fecha)
    ).scalars().first()

    if existente:
        existente.tasa_oficial = tasa_oficial
        if tasa_bcv is not None:
            existente.tasa_bcv = tasa_bcv
        if tasa_binance is not None:
            existente.tasa_binance = tasa_binance
        existente.usuario_id = usuario_id
        existente.usuario_email = usuario_email
        existente.updated_at = datetime.now()
    else:
        existente = TasaCambioDiaria(
            fecha=fecha,
            tasa_oficial=tasa_oficial,
            tasa_bcv=tasa_bcv,
            tasa_binance=tasa_binance,
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


def _columna_tasa_presente_y_valida(val: Any) -> bool:
    """True si hay valor numérico usable (no None, no problemático)."""
    if val is None:
        return False
    return not es_tasa_problematica_para_operacion(val)


def estado_multifuente_fila_hoy(row: Optional[TasaCambioDiaria]) -> dict[str, bool]:
    """
    Para la fila del día (hoy Caracas): qué columnas Euro / BCV / Binance están cargadas y válidas.
    Misma validación numérica que `tasa_oficial` (positiva, no placeholder).
    """
    if row is None:
        return {"euro_ok": False, "bcv_ok": False, "binance_ok": False}
    return {
        "euro_ok": _columna_tasa_presente_y_valida(row.tasa_oficial),
        "bcv_ok": _columna_tasa_presente_y_valida(getattr(row, "tasa_bcv", None)),
        "binance_ok": _columna_tasa_presente_y_valida(getattr(row, "tasa_binance", None)),
    }


def fila_tasa_multifuente_completa_hoy(row: Optional[TasaCambioDiaria]) -> bool:
    """Día completo cuando las tres fuentes tienen tasa válida en la misma fila."""
    st = estado_multifuente_fila_hoy(row)
    return bool(st["euro_ok"] and st["bcv_ok"] and st["binance_ok"])
