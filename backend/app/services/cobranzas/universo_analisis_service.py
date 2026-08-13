"""Analisis de cobranzas alineado a segmentos del dashboard/menu."""

from __future__ import annotations

import io
import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from typing import Any, Optional, Sequence

from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants.prestamo_estados import ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF
from app.models.cobranza_universo import CobranzaUniversoCedula, CobranzaUniversoDesempenoDiario
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.prestamo import Prestamo
from app.services.cuota_estado import (
    TZ_NEGOCIO,
    dias_retraso_desde_vencimiento,
    hoy_negocio,
)
from app.services.notificaciones_exclusion_desistimiento import sql_cliente_sin_desistimiento
from app.services.desempeno_1_cuota_stock import (
    SEG_MAX_N_EXACTO,
    SEG_MIN_DIAS_CUOTA_1,
    _cumple_ventana_6plus,
    _cumple_ventana_segmento,
    _load_cuotas_meta,
    _stock_1_cuota_excluyendo_prejudicial_at,
    _stock_2_cuotas_at,
    _stock_3_cuotas_at,
    _stock_4_cuotas_at,
    _stock_5_cuotas_at,
    _stock_6plus_cuotas_at,
    _stock_exact_n_cuotas_at,
    _t_fin_dia,
)
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    normalizar_cedula_almacenamiento,
    texto_cedula_comparable_bd,
)

logger = logging.getLogger(__name__)

_HEADER_CELLS = frozenset({"cedula", "cedulas", "documento", "id"})
# Gráficos diarios (serie): 1..5 exactas + 6+ sin techo.
_BUCKET_KEYS = ("1", "2", "3", "4", "5", "6plus")
# Tabla + detalle: 1..15 exactas (tope n*30) + resto del viejo 6+ (sin techo).
_RESTO_6PLUS_KEY = "resto6plus"
_TABLA_BUCKET_KEYS = tuple(str(i) for i in range(1, SEG_MAX_N_EXACTO + 1)) + (
    _RESTO_6PLUS_KEY,
)


def expr_prestamo_activo_cobranzas():
    """Misma cartera que dashboard/notificaciones: no LIQUIDADO ni DESISTIMIENTO."""
    est = func.upper(func.trim(func.coalesce(Prestamo.estado, "")))
    excl = tuple(str(e).strip().upper() for e in ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF)
    return est.notin_(excl)


def prestamo_es_activo_cobranzas(estado: Optional[str]) -> bool:
    return (estado or "").strip().upper() not in {
        str(e).strip().upper() for e in ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF
    }


def _texto_celda_a(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bool):
        return str(raw).strip()
    if isinstance(raw, int):
        return str(raw)
    if isinstance(raw, float):
        if raw == int(raw):
            return str(int(raw))
        return str(raw).strip()
    return str(raw).strip()


def _es_celda_header(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    # quitar acentos basicos en encabezados tipicos
    t = (
        t.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    return t in _HEADER_CELLS


def parse_cedulas_desde_excel(content: bytes) -> list[str]:
    """Lee cedulas de la columna A (openpyxl). Omite encabezados y duplicados."""
    try:
        from openpyxl import load_workbook
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="Dependencia openpyxl no disponible en el servidor.",
        ) from e

    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        ws = wb.active
        if ws is None:
            return []
        out: list[str] = []
        seen: set[str] = set()
        for row in ws.iter_rows(min_col=1, max_col=1, values_only=True):
            raw = row[0] if row else None
            text = _texto_celda_a(raw)
            if not text or _es_celda_header(text):
                continue
            store = normalizar_cedula_almacenamiento(text)
            if not store:
                continue
            key = texto_cedula_comparable_bd(store)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(store)
        return out
    finally:
        wb.close()


def reemplazar_universo(
    db: Session,
    cedulas: Sequence[str],
    usuario_id: Optional[int] = None,
) -> int:
    """Reemplazo total (interno). Prefiera fusionar_universo para carga Excel."""
    db.query(CobranzaUniversoDesempenoDiario).delete()
    db.query(CobranzaUniversoCedula).delete()
    n = 0
    for c in cedulas:
        store = normalizar_cedula_almacenamiento(c)
        if not store:
            continue
        db.add(CobranzaUniversoCedula(cedula=store, usuario_id=usuario_id))
        n += 1
    db.commit()
    return n


def listar_cedulas_universo(db: Session) -> list[str]:
    """Cedulas del universo, ordenadas."""
    rows = db.query(CobranzaUniversoCedula.cedula).all()
    out = [str(c) for (c,) in rows if c]
    return sorted(out)


def fusionar_universo(
    db: Session,
    cedulas: Sequence[str],
    usuario_id: Optional[int] = None,
) -> dict[str, Any]:
    """Inserta solo cedulas nuevas (por clave comparable). No borra snapshots."""
    existentes = claves_universo(db)
    agregadas = 0
    ya_existian = 0
    seen_batch: set[str] = set()
    for c in cedulas:
        store = normalizar_cedula_almacenamiento(c)
        if not store:
            continue
        key = texto_cedula_comparable_bd(store)
        if not key:
            continue
        if key in existentes or key in seen_batch:
            ya_existian += 1
            continue
        seen_batch.add(key)
        db.add(CobranzaUniversoCedula(cedula=store, usuario_id=usuario_id))
        agregadas += 1
    if agregadas:
        db.commit()
    cantidad = contar_universo(db)
    return {
        "agregadas": agregadas,
        "ya_existian": ya_existian,
        "cantidad": cantidad,
        "meta": meta_universo(db),
    }


def agregar_cedula_universo(
    db: Session,
    cedula_raw: str,
    usuario_id: Optional[int] = None,
) -> dict[str, Any]:
    store = normalizar_cedula_almacenamiento(cedula_raw)
    if not store:
        raise HTTPException(status_code=400, detail="Cedula invalida o vacia.")
    key = texto_cedula_comparable_bd(store)
    if not key:
        raise HTTPException(status_code=400, detail="Cedula invalida o vacia.")
    if key in claves_universo(db):
        return {
            "cedula": store,
            "agregada": False,
            "cantidad": contar_universo(db),
        }
    db.add(CobranzaUniversoCedula(cedula=store, usuario_id=usuario_id))
    db.commit()
    return {
        "cedula": store,
        "agregada": True,
        "cantidad": contar_universo(db),
    }


def eliminar_cedula_universo(db: Session, cedula_raw: str) -> dict[str, Any]:
    store = normalizar_cedula_almacenamiento(cedula_raw)
    if not store:
        raise HTTPException(status_code=400, detail="Cedula invalida o vacia.")
    key = texto_cedula_comparable_bd(store)
    if not key:
        raise HTTPException(status_code=400, detail="Cedula invalida o vacia.")
    eliminada = False
    rows = db.query(CobranzaUniversoCedula).all()
    for row in rows:
        if texto_cedula_comparable_bd(row.cedula) == key:
            db.delete(row)
            eliminada = True
    if eliminada:
        db.commit()
    return {
        "cedula": store,
        "eliminada": eliminada,
        "cantidad": contar_universo(db),
    }


async def upload_universo_excel(
    db: Session,
    file: UploadFile,
    usuario_id: Optional[int] = None,
) -> dict[str, Any]:
    nombre = (file.filename or "").lower()
    if not nombre.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Debe subir un archivo Excel (.xlsx o .xls)",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacio.")
    cedulas = parse_cedulas_desde_excel(content)
    if not cedulas:
        raise HTTPException(
            status_code=400,
            detail="No se encontraron cedulas en la columna A del Excel.",
        )
    return fusionar_universo(db, cedulas, usuario_id=usuario_id)


def contar_universo(db: Session) -> int:
    return int(db.query(CobranzaUniversoCedula).count() or 0)


def claves_universo(db: Session) -> set[str]:
    rows = db.query(CobranzaUniversoCedula.cedula).all()
    out: set[str] = set()
    for (ced,) in rows:
        k = texto_cedula_comparable_bd(ced)
        if k:
            out.add(k)
    return out


def cedula_en_universo(db: Session, cedula_raw: str) -> bool:
    """Compat: ya no hay filtro Excel; cualquier cedula valida puede buscarse."""
    del db  # no usado
    key = texto_cedula_comparable_bd(cedula_raw)
    return bool(key)


def meta_universo(db: Session) -> dict[str, Any]:
    rows = (
        db.query(CobranzaUniversoCedula)
        .order_by(CobranzaUniversoCedula.creado_en.desc())
        .limit(1)
        .all()
    )
    cantidad = contar_universo(db)
    if not rows:
        return {"cantidad": 0, "cargado_en": None, "usuario_id": None}
    r = rows[0]
    return {
        "cantidad": cantidad,
        "cargado_en": r.creado_en,
        "usuario_id": r.usuario_id,
    }


def limpiar_universo(db: Session) -> dict[str, Any]:
    n_ced = db.query(CobranzaUniversoCedula).delete()
    db.query(CobranzaUniversoDesempenoDiario).delete()
    db.commit()
    return {"eliminados": int(n_ced or 0)}


def _bucket_clave(n_vencidas: int) -> Optional[str]:
    """Compat: conteo exacto sin filtro de dias (tests / callers simples)."""
    if n_vencidas <= 0:
        return None
    if n_vencidas == 1:
        return "1"
    if n_vencidas == 2:
        return "2"
    if n_vencidas == 3:
        return "3"
    if n_vencidas == 4:
        return "4"
    if n_vencidas == 5:
        return "5"
    return "6plus"


def _bucket_clave_desde_atrasos(dias_atraso: list[int]) -> Optional[str]:
    """Misma ventana que dashboard: 1→1-30 … 5→6-150, 6+→>=6."""
    n = len(dias_atraso)
    if n <= 0:
        return None
    if n == 1 and _cumple_ventana_segmento(dias_atraso, 1):
        return "1"
    if n == 2 and _cumple_ventana_segmento(dias_atraso, 2):
        return "2"
    if n == 3 and _cumple_ventana_segmento(dias_atraso, 3):
        return "3"
    if n == 4 and _cumple_ventana_segmento(dias_atraso, 4):
        return "4"
    if n == 5 and _cumple_ventana_segmento(dias_atraso, 5):
        return "5"
    if n >= 6 and _cumple_ventana_6plus(dias_atraso):
        return "6plus"
    return None


def _aplicar_exclusion_cliente_bucket_1(
    filas: list[tuple[int, Optional[int], str, float]],
) -> list[tuple[int, Optional[int], str, float]]:
    """Quita del bucket 1 a prestamos cuyo cliente tiene otro con >=2 atrasadas.

    Misma exclusion mutua que `_stock_1_cuota_excluyendo_prejudicial_at`.
    `filas`: (prestamo_id, cliente_id, bucket, saldo_usd).
    """
    clientes_ge2: set[int] = set()
    for _pid, cid, bucket, _saldo in filas:
        if bucket in ("2", "3", "4", "5", "6plus") and cid is not None:
            clientes_ge2.add(int(cid))
    if not clientes_ge2:
        return filas
    out: list[tuple[int, Optional[int], str, float]] = []
    for pid, cid, bucket, saldo in filas:
        if bucket == "1" and cid is not None and int(cid) in clientes_ge2:
            continue
        out.append((pid, cid, bucket, saldo))
    return out


def _empty_buckets() -> dict[str, dict[str, Any]]:
    return {
        k: {"clave": k, "cantidad": 0, "monto_usd": 0.0, "items": []}
        for k in _TABLA_BUCKET_KEYS
    }


def _upsert_snapshot_hoy(
    db: Session,
    hoy: date,
    montos: dict[str, Decimal],
    cantidades: dict[str, int],
) -> None:
    for b in _BUCKET_KEYS:
        row = (
            db.query(CobranzaUniversoDesempenoDiario)
            .filter(
                CobranzaUniversoDesempenoDiario.fecha == hoy,
                CobranzaUniversoDesempenoDiario.bucket == b,
            )
            .first()
        )
        monto = montos.get(b, Decimal("0"))
        cant = int(cantidades.get(b, 0) or 0)
        if row:
            row.monto_usd = monto
            row.cantidad_prestamos = cant
        else:
            db.add(
                CobranzaUniversoDesempenoDiario(
                    fecha=hoy,
                    bucket=b,
                    monto_usd=monto,
                    cantidad_prestamos=cant,
                )
            )
    db.commit()


_TOL_SALDO_COBRANZAS = 0.01


def _as_date_caracas(value: date | datetime | None, z: ZoneInfo) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(z).date()
    return value


def _pagado_al_dia(
    *,
    monto: float,
    fecha_pago: date | None,
    eventos: list[tuple[date, float]],
    dia: date,
    total_pagado_actual: float,
    es_hoy: bool,
) -> float:
    """Monto ya aplicado a la cuota al cierre de `dia` (as-of).

    - Suma cuota_pagos con fecha_aplicacion <= dia.
    - Si fecha_pago <= dia y aun no cubre, trata como liquidada ese dia.
    - Solo en `es_hoy` usa total_pagado actual (puede ir adelante de eventos).
      Asi un cobro de hoy baja HOY pero no reescribe AYER/lunes.
    """
    paid = 0.0
    for fd, m in eventos:
        if fd <= dia:
            paid += float(m or 0)
    monto_f = float(monto or 0)
    if (
        fecha_pago is not None
        and fecha_pago <= dia
        and paid + _TOL_SALDO_COBRANZAS < monto_f
    ):
        paid = monto_f
    if es_hoy:
        paid = max(paid, float(total_pagado_actual or 0))
    return paid


def _cuota_vencida_saldo_en_fecha(
    monto: float,
    fecha_vencimiento: date | None,
    fecha_pago: date | None,
    dia: date,
    pagado_al_dia: float,
) -> Optional[float]:
    """Saldo residual de cuota vencida en `dia` (as-of), o None si no cuenta.

    Usa `pagado_al_dia` (aplicaciones hasta ese dia), no el total_pagado futuro.
    Asi se ve mejora: ayer incluye deuda cobrada hoy; hoy ya no.
    """
    if dias_retraso_desde_vencimiento(fecha_vencimiento, dia) < 1:
        return None
    monto_f = float(monto or 0)
    paid = float(pagado_al_dia or 0)
    if paid + _TOL_SALDO_COBRANZAS >= monto_f:
        return None
    return max(0.0, monto_f - paid)


def _load_eventos_por_cuota(
    db: Session, cuota_ids: Sequence[int], z: ZoneInfo
) -> dict[int, list[tuple[date, float]]]:
    """fecha_aplicacion (Caracas) + monto_aplicado por cuota_id."""
    out: dict[int, list[tuple[date, float]]] = {int(i): [] for i in cuota_ids}
    if not cuota_ids:
        return out
    chunk = 2000
    ids = [int(i) for i in cuota_ids]
    for i in range(0, len(ids), chunk):
        batch = ids[i : i + chunk]
        rows = (
            db.query(
                CuotaPago.cuota_id,
                CuotaPago.fecha_aplicacion,
                CuotaPago.monto_aplicado,
            )
            .filter(CuotaPago.cuota_id.in_(batch))
            .all()
        )
        for cid, fa, mon in rows:
            fd = _as_date_caracas(fa, z)
            if fd is None:
                continue
            out.setdefault(int(cid), []).append((fd, float(mon or 0)))
    for cid in out:
        out[cid].sort(key=lambda x: x[0])
    return out


def _metricas_prestamo_en_fecha(
    cuotas: list[Cuota],
    eventos_por_cuota: dict[int, list[tuple[date, float]]],
    dia: date,
    hoy: date,
) -> tuple[Optional[str], float, list[int]]:
    """Devuelve (bucket|None, saldo_usd, dias_atraso_por_cuota_vencida)."""
    es_hoy = dia == hoy
    dias: list[int] = []
    saldo = 0.0
    for c in cuotas:
        monto = float(c.monto or 0)
        paid_act = float(c.total_pagado or 0)
        fv = c.fecha_vencimiento
        fp = c.fecha_pago if isinstance(c.fecha_pago, date) else None
        da = dias_retraso_desde_vencimiento(fv, dia)
        if da < SEG_MIN_DIAS_CUOTA_1:
            continue
        pagado = _pagado_al_dia(
            monto=monto,
            fecha_pago=fp,
            eventos=eventos_por_cuota.get(int(c.id), []),
            dia=dia,
            total_pagado_actual=paid_act,
            es_hoy=es_hoy,
        )
        s = _cuota_vencida_saldo_en_fecha(monto, fv, fp, dia, pagado)
        if s is None:
            continue
        dias.append(int(da))
        saldo += s
    return _bucket_clave_desde_atrasos(dias), round(saldo, 2), dias


_STOCK_FN_POR_BUCKET = {
    "1": _stock_1_cuota_excluyendo_prejudicial_at,
    "2": _stock_2_cuotas_at,
    "3": _stock_3_cuotas_at,
    "4": _stock_4_cuotas_at,
    "5": _stock_5_cuotas_at,
    "6plus": _stock_6plus_cuotas_at,
}


def _stock_resto6plus_at(
    cuotas_meta: list[dict[str, Any]], t_ref: datetime, z: ZoneInfo
) -> set[int]:
    """6+ sin techo menos exactamente 6..15 en ventana n*30 (partición sin solape)."""
    base = _stock_6plus_cuotas_at(cuotas_meta, t_ref, z)
    if not base:
        return set()
    for n in range(6, SEG_MAX_N_EXACTO + 1):
        base -= _stock_exact_n_cuotas_at(cuotas_meta, t_ref, z, n)
    return base


def _stock_fn_tabla(key: str):
    if key == "1":
        return _stock_1_cuota_excluyendo_prejudicial_at
    if key == _RESTO_6PLUS_KEY:
        return _stock_resto6plus_at
    n = int(key)
    return lambda meta, t, z, n=n: _stock_exact_n_cuotas_at(meta, t, z, n)


_STOCK_FN_TABLA = {k: _stock_fn_tabla(k) for k in _TABLA_BUCKET_KEYS}


def _sets_fin_dia_por_bucket(
    cuotas_meta: list[dict[str, Any]],
    dia: date,
    hoy: date,
    now_z: datetime,
    z: ZoneInfo,
    *,
    stock_fns: Optional[dict[str, Any]] = None,
) -> dict[str, set[int]]:
    """Misma CANTIDAD que dashboard Fin dia: stock_00h ∩ stock_fin."""
    fns = stock_fns or _STOCK_FN_POR_BUCKET
    t0 = datetime.combine(dia, time(0, 0, 0), tzinfo=z)
    t_fin = _t_fin_dia(dia, hoy, now_z, z)
    out: dict[str, set[int]] = {}
    for key, fn in fns.items():
        if not cuotas_meta:
            out[key] = set()
            continue
        set_00 = fn(cuotas_meta, t0, z)
        set_fin = fn(cuotas_meta, t_fin, z)
        out[key] = set_00 & set_fin
    return out


def _saldo_usd_prestamo_en_fecha(
    cuotas: list[Cuota],
    eventos_por_cuota: dict[int, list[tuple[date, float]]],
    dia: date,
    hoy: date,
) -> tuple[float, int]:
    """Saldo residual as-of + numero de cuotas vencidas con saldo (para detalle)."""
    _bucket, saldo, dias = _metricas_prestamo_en_fecha(
        cuotas, eventos_por_cuota, dia, hoy
    )
    return float(saldo or 0), len(dias)


def _buckets_metricas_en_fecha(
    by_pid: dict[int, list[Cuota]],
    eventos_por_cuota: dict[int, list[tuple[date, float]]],
    cuotas_meta: list[dict[str, Any]],
    dia: date,
    hoy: date,
    now_z: datetime,
    z: ZoneInfo,
    *,
    bucket_keys: Sequence[str] = _BUCKET_KEYS,
    stock_fns: Optional[dict[str, Any]] = None,
) -> tuple[dict[str, float], dict[str, int], dict[str, set[int]]]:
    """Cantidad = Fin dia dashboard; monto = saldo as-of de esos prestamos."""
    keys = tuple(bucket_keys)
    montos: dict[str, float] = {k: 0.0 for k in keys}
    cants: dict[str, int] = {k: 0 for k in keys}
    sets = _sets_fin_dia_por_bucket(
        cuotas_meta, dia, hoy, now_z, z, stock_fns=stock_fns
    )
    for key in keys:
        pids = sets.get(key) or set()
        cants[key] = len(pids)
        total = 0.0
        for pid in pids:
            saldo, _n = _saldo_usd_prestamo_en_fecha(
                by_pid.get(int(pid), []), eventos_por_cuota, dia, hoy
            )
            total += saldo
        montos[key] = round(total, 2)
    return montos, cants, sets


def _punto_serie_vacio(d: date) -> dict[str, Any]:
    return {
        "fecha": d,
        "monto_1": 0.0,
        "monto_2": 0.0,
        "monto_3": 0.0,
        "monto_4": 0.0,
        "monto_5": 0.0,
        "monto_6plus": 0.0,
        "cantidad_1": 0,
        "cantidad_2": 0,
        "cantidad_3": 0,
        "cantidad_4": 0,
        "cantidad_5": 0,
        "cantidad_6plus": 0,
    }


def _punto_serie_desde_metricas(
    d: date, montos: dict[str, float], cants: dict[str, int]
) -> dict[str, Any]:
    return {
        "fecha": d,
        "monto_1": float(montos.get("1", 0) or 0),
        "monto_2": float(montos.get("2", 0) or 0),
        "monto_3": float(montos.get("3", 0) or 0),
        "monto_4": float(montos.get("4", 0) or 0),
        "monto_5": float(montos.get("5", 0) or 0),
        "monto_6plus": float(montos.get("6plus", 0) or 0),
        "cantidad_1": int(cants.get("1", 0) or 0),
        "cantidad_2": int(cants.get("2", 0) or 0),
        "cantidad_3": int(cants.get("3", 0) or 0),
        "cantidad_4": int(cants.get("4", 0) or 0),
        "cantidad_5": int(cants.get("5", 0) or 0),
        "cantidad_6plus": int(cants.get("6plus", 0) or 0),
    }


def _serie_diaria_30_vacia(hoy: date) -> list[dict[str, Any]]:
    """30 dias calendario terminando en hoy, todos en cero."""
    return [_punto_serie_vacio(hoy - timedelta(days=29 - i)) for i in range(30)]


def _serie_diaria_30_desde_universo(
    by_pid: dict[int, list[Cuota]],
    eventos_por_cuota: dict[int, list[tuple[date, float]]],
    cuotas_meta: list[dict[str, Any]],
    hoy: date,
    now_z: datetime,
    z: ZoneInfo,
) -> list[dict[str, Any]]:
    """30 dias: cantidad Fin dia (dashboard) + monto residual as-of."""
    serie: list[dict[str, Any]] = []
    for i in range(30):
        dia = hoy - timedelta(days=29 - i)
        montos, cants, _sets = _buckets_metricas_en_fecha(
            by_pid, eventos_por_cuota, cuotas_meta, dia, hoy, now_z, z
        )
        serie.append(_punto_serie_desde_metricas(dia, montos, cants))
    return serie


def _pct_var(actual: float, base: float) -> Optional[float]:
    if abs(base) < 0.005:
        if abs(actual) < 0.005:
            return 0.0
        return None
    return round(((actual - base) / abs(base)) * 100.0, 2)


def _fechas_3_lunes_ayer_hoy(hoy: date) -> list[date]:
    """3 lunes previos (sin repetir ayer) + ayer + hoy. Siempre 5 fechas distintas."""
    ayer = hoy - timedelta(days=1)
    cursor = hoy - timedelta(days=1)
    while cursor.weekday() != 0:  # lunes = 0
        cursor -= timedelta(days=1)
    if cursor == ayer:
        cursor -= timedelta(days=7)
    lunes: list[date] = []
    for _ in range(3):
        lunes.append(cursor)
        cursor -= timedelta(days=7)
    lunes.reverse()
    return lunes + [ayer, hoy]


def _etiqueta_lectura(d: date, hoy: date) -> str:
    dd = d.strftime("%d/%m")
    if d == hoy:
        return f"Hoy {dd}"
    if d == hoy - timedelta(days=1):
        return f"Ayer {dd}"
    if d.weekday() == 0:
        return f"Lun {dd}"
    return dd


def _lecturas_lunes_desempeno(
    by_pid: dict[int, list[Cuota]],
    eventos_por_cuota: dict[int, list[tuple[date, float]]],
    cuotas_meta: list[dict[str, Any]],
    hoy: date,
    now_z: datetime,
    z: ZoneInfo,
) -> dict[str, Any]:
    """Cantidad = Fin dia dashboard; monto = saldo as-of. Filas exactas 1..15."""
    fechas = _fechas_3_lunes_ayer_hoy(hoy)
    ayer = hoy - timedelta(days=1)
    snaps: list[tuple[date, dict[str, float], dict[str, int]]] = []
    for dia in fechas:
        montos, cants, _sets = _buckets_metricas_en_fecha(
            by_pid,
            eventos_por_cuota,
            cuotas_meta,
            dia,
            hoy,
            now_z,
            z,
            bucket_keys=_TABLA_BUCKET_KEYS,
            stock_fns=_STOCK_FN_TABLA,
        )
        snaps.append((dia, montos, cants))

    columnas = [
        {
            "fecha": dia.isoformat(),
            "etiqueta": _etiqueta_lectura(dia, hoy),
            "es_hoy": dia == hoy,
            "es_ayer": dia == ayer,
        }
        for dia, _, _ in snaps
    ]

    buckets_out: dict[str, Any] = {}
    for b in _TABLA_BUCKET_KEYS:
        lecturas = []
        for dia, montos, cants in snaps:
            lecturas.append(
                {
                    "fecha": dia.isoformat(),
                    "cantidad": int(cants.get(b, 0) or 0),
                    "monto_usd": float(montos.get(b, 0) or 0),
                }
            )
        buckets_out[b] = {"clave": b, "lecturas": lecturas}

    total_lecturas = []
    for dia, montos, cants in snaps:
        total_lecturas.append(
            {
                "fecha": dia.isoformat(),
                "cantidad": int(
                    sum(int(cants.get(k, 0) or 0) for k in _TABLA_BUCKET_KEYS)
                ),
                "monto_usd": round(
                    sum(float(montos.get(k, 0) or 0) for k in _TABLA_BUCKET_KEYS), 2
                ),
            }
        )

    return {
        "columnas": columnas,
        "buckets": buckets_out,
        "total": {"clave": "total", "lecturas": total_lecturas},
    }


def analizar_universo(db: Session) -> dict[str, Any]:
    """Cobranzas: CANTIDAD = Fin dia del dashboard; MONTO = saldo as-of USD.

    Sin tocar dashboard. Cartera sin LIQUIDADO/DESISTIMIENTO.
    """
    buckets = _empty_buckets()
    sin_vencidas = 0
    hoy = hoy_negocio()
    z = ZoneInfo(TZ_NEGOCIO)
    now_z = datetime.now(z)

    prestamos = (
        db.query(Prestamo)
        .filter(expr_prestamo_activo_cobranzas())
        .filter(sql_cliente_sin_desistimiento())
        .all()
    )
    meta = {
        "cantidad": len(prestamos),
        "cargado_en": None,
        "usuario_id": None,
        "fuente": "bd_completa",
        "segmentacion": "dashboard_fin_dia",
        "cantidad_origen": "dashboard_stock_23h",
        "monto_origen": "saldo_asof_usd",
    }
    pids = [int(p.id) for p in prestamos]
    prestamo_by_id: dict[int, Prestamo] = {int(p.id): p for p in prestamos}

    by_pid: dict[int, list[Cuota]] = defaultdict(list)
    cuota_ids: list[int] = []
    if pids:
        for c in db.query(Cuota).filter(Cuota.prestamo_id.in_(pids)).all():
            by_pid[int(c.prestamo_id)].append(c)
            cuota_ids.append(int(c.id))

    eventos_por_cuota = _load_eventos_por_cuota(db, cuota_ids, z)

    # Meta de stock identica al dashboard (1 cuota / 2 / 3 / 4+).
    fv_max = hoy - timedelta(days=1)
    cuotas_meta = _load_cuotas_meta(db, fv_min=None, fv_max=fv_max, z=z)

    montos_snap: dict[str, Decimal] = {k: Decimal("0") for k in _BUCKET_KEYS}
    cant_snap: dict[str, int] = {k: 0 for k in _BUCKET_KEYS}

    for pid in pids:
        _b, _saldo, dias = _metricas_prestamo_en_fecha(
            by_pid.get(pid, []), eventos_por_cuota, hoy, hoy
        )
        if not dias:
            sin_vencidas += 1

    # Detalle + totales alineados a la tabla (1..15 + resto6plus).
    montos_hoy, cants_hoy, sets_hoy = _buckets_metricas_en_fecha(
        by_pid,
        eventos_por_cuota,
        cuotas_meta,
        hoy,
        hoy,
        now_z,
        z,
        bucket_keys=_TABLA_BUCKET_KEYS,
        stock_fns=_STOCK_FN_TABLA,
    )

    for key in _TABLA_BUCKET_KEYS:
        for pid in sorted(sets_hoy.get(key) or set()):
            p = prestamo_by_id.get(int(pid))
            if p is None:
                continue
            saldo_r, n_venc = _saldo_usd_prestamo_en_fecha(
                by_pid.get(int(pid), []), eventos_por_cuota, hoy, hoy
            )
            item = {
                "prestamo_id": int(pid),
                "cedula": p.cedula or "",
                "nombres": p.nombres,
                "cuotas_vencidas": int(n_venc),
                "saldo_vencido_usd": float(saldo_r),
            }
            buckets[key]["items"].append(item)
        buckets[key]["cantidad"] = int(cants_hoy.get(key, 0) or 0)
        buckets[key]["monto_usd"] = float(montos_hoy.get(key, 0) or 0)

    # Snapshot/serie diaria de gráficos: sigue 1..5 + 6plus.
    montos_chart, cants_chart, _sets_chart = _buckets_metricas_en_fecha(
        by_pid, eventos_por_cuota, cuotas_meta, hoy, hoy, now_z, z
    )
    for key in _BUCKET_KEYS:
        montos_snap[key] = Decimal(str(montos_chart.get(key, 0) or 0))
        cant_snap[key] = int(cants_chart.get(key, 0) or 0)

    _upsert_snapshot_hoy(db, hoy, montos_snap, cant_snap)

    serie = _serie_diaria_30_desde_universo(
        by_pid, eventos_por_cuota, cuotas_meta, hoy, now_z, z
    )

    meta["cantidad"] = len(prestamos)
    return {
        "buckets": buckets,
        "sin_vencidas": sin_vencidas,
        "serie_diaria": serie,
        "desempeno_lecturas": _lecturas_lunes_desempeno(
            by_pid, eventos_por_cuota, cuotas_meta, hoy, now_z, z
        ),
        "meta": meta,
    }
