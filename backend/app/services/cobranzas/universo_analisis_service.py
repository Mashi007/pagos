"""Analisis de cobranzas alineado a segmentos del dashboard/menu."""

from __future__ import annotations

import io
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
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
from app.services.notificacion_service import (
    MAX_DIAS_ATRASO_PARA_LISTADO_10_DIAS,
    MIN_DIAS_ATRASO_PARA_LISTADO_10_DIAS,
    MIN_DIAS_ATRASO_PREJUDICIAL,
)
from app.services.notificaciones_exclusion_desistimiento import sql_cliente_sin_desistimiento
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    normalizar_cedula_almacenamiento,
    texto_cedula_comparable_bd,
)

logger = logging.getLogger(__name__)

_HEADER_CELLS = frozenset({"cedula", "cedulas", "documento", "id"})
_BUCKET_KEYS = ("1", "2", "3", "4plus")


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
    return "4plus"


def _bucket_clave_desde_atrasos(dias_atraso: list[int]) -> Optional[str]:
    """Buckets alineados al dashboard/menu.

    - 1 cuota: exactamente 1 atrasada Y atraso en [6, 59] dias.
      Si tiene 1 atrasada fuera de ese rango, no entra en ningun bucket.
    - 2 / 3 / 4+: exactamente 2 / 3 / >=4 con atraso >= MIN_DIAS_ATRASO_PREJUDICIAL.
    """
    n = len(dias_atraso)
    if n <= 0:
        return None
    if n == 1:
        da = int(dias_atraso[0])
        if (
            MIN_DIAS_ATRASO_PARA_LISTADO_10_DIAS
            <= da
            <= MAX_DIAS_ATRASO_PARA_LISTADO_10_DIAS
        ):
            return "1"
        return None
    if n == 2:
        return "2"
    if n == 3:
        return "3"
    # n >= 4
    return "4plus"


def _aplicar_exclusion_cliente_bucket_1(
    filas: list[tuple[int, Optional[int], str, float]],
) -> list[tuple[int, Optional[int], str, float]]:
    """Quita del bucket 1 a prestamos cuyo cliente tiene otro con >=2 atrasadas.

    Misma exclusion mutua que `_stock_1_cuota_excluyendo_prejudicial_at`.
    `filas`: (prestamo_id, cliente_id, bucket, saldo_usd).
    """
    clientes_ge2: set[int] = set()
    for _pid, cid, bucket, _saldo in filas:
        if bucket in ("2", "3", "4plus") and cid is not None:
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
        for k in _BUCKET_KEYS
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
        if da < MIN_DIAS_ATRASO_PREJUDICIAL:
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


def _buckets_metricas_en_fecha(
    prestamo_ids: Sequence[int],
    by_pid: dict[int, list[Cuota]],
    eventos_por_cuota: dict[int, list[tuple[date, float]]],
    pid_to_cliente: dict[int, Optional[int]],
    dia: date,
    hoy: date,
) -> tuple[dict[str, float], dict[str, int]]:
    """Montos USD y cantidad por bucket en `dia` (as-of + reglas dashboard)."""
    montos: dict[str, float] = {k: 0.0 for k in _BUCKET_KEYS}
    cants: dict[str, int] = {k: 0 for k in _BUCKET_KEYS}
    filas: list[tuple[int, Optional[int], str, float]] = []
    for pid in prestamo_ids:
        bucket, saldo, _dias = _metricas_prestamo_en_fecha(
            by_pid.get(pid, []), eventos_por_cuota, dia, hoy
        )
        if not bucket:
            continue
        filas.append((int(pid), pid_to_cliente.get(int(pid)), bucket, float(saldo)))
    for _pid, _cid, bucket, saldo in _aplicar_exclusion_cliente_bucket_1(filas):
        montos[bucket] = round(montos[bucket] + saldo, 2)
        cants[bucket] += 1
    return montos, cants


def _punto_serie_vacio(d: date) -> dict[str, Any]:
    return {
        "fecha": d,
        "monto_1": 0.0,
        "monto_2": 0.0,
        "monto_3": 0.0,
        "monto_4plus": 0.0,
        "cantidad_1": 0,
        "cantidad_2": 0,
        "cantidad_3": 0,
        "cantidad_4plus": 0,
    }


def _punto_serie_desde_metricas(
    d: date, montos: dict[str, float], cants: dict[str, int]
) -> dict[str, Any]:
    return {
        "fecha": d,
        "monto_1": float(montos.get("1", 0) or 0),
        "monto_2": float(montos.get("2", 0) or 0),
        "monto_3": float(montos.get("3", 0) or 0),
        "monto_4plus": float(montos.get("4plus", 0) or 0),
        "cantidad_1": int(cants.get("1", 0) or 0),
        "cantidad_2": int(cants.get("2", 0) or 0),
        "cantidad_3": int(cants.get("3", 0) or 0),
        "cantidad_4plus": int(cants.get("4plus", 0) or 0),
    }


def _serie_diaria_30_vacia(hoy: date) -> list[dict[str, Any]]:
    """30 dias calendario terminando en hoy, todos en cero."""
    return [_punto_serie_vacio(hoy - timedelta(days=29 - i)) for i in range(30)]


def _serie_diaria_30_desde_universo(
    prestamo_ids: Sequence[int],
    by_pid: dict[int, list[Cuota]],
    eventos_por_cuota: dict[int, list[tuple[date, float]]],
    pid_to_cliente: dict[int, Optional[int]],
    hoy: date,
) -> list[dict[str, Any]]:
    """Reconstruye 30 dias (hoy-29..hoy): saldo as-of y cantidad de prestamos."""
    serie: list[dict[str, Any]] = []
    for i in range(30):
        dia = hoy - timedelta(days=29 - i)
        montos, cants = _buckets_metricas_en_fecha(
            prestamo_ids, by_pid, eventos_por_cuota, pid_to_cliente, dia, hoy
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
    # Si ayer es lunes, no lo cuentes otra vez en la serie de lunes.
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
    prestamo_ids: Sequence[int],
    by_pid: dict[int, list[Cuota]],
    eventos_por_cuota: dict[int, list[tuple[date, float]]],
    pid_to_cliente: dict[int, Optional[int]],
    hoy: date,
) -> dict[str, Any]:
    """Cantidades y montos as-of en 3 lunes previos + ayer + hoy. Sin deltas."""
    fechas = _fechas_3_lunes_ayer_hoy(hoy)
    ayer = hoy - timedelta(days=1)
    snaps: list[tuple[date, dict[str, float], dict[str, int]]] = []
    for dia in fechas:
        montos, cants = _buckets_metricas_en_fecha(
            prestamo_ids, by_pid, eventos_por_cuota, pid_to_cliente, dia, hoy
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
    for b in _BUCKET_KEYS:
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
                "cantidad": int(sum(int(cants.get(k, 0) or 0) for k in _BUCKET_KEYS)),
                "monto_usd": round(
                    sum(float(montos.get(k, 0) or 0) for k in _BUCKET_KEYS), 2
                ),
            }
        )

    return {
        "columnas": columnas,
        "buckets": buckets_out,
        "total": {"clave": "total", "lecturas": total_lecturas},
    }


def analizar_universo(db: Session) -> dict[str, Any]:
    """Buckets alineados al dashboard/menu (opcion 1).

    Cartera: no LIQUIDADO/DESISTIMIENTO + cliente sin DESISTIMIENTO.
    1 cuota: atraso 6-59 y exclusion por cliente con >=2 atrasadas.
    2/3/4+: excluyentes por conteo. Monto = saldo as-of (USD).
    """
    buckets = _empty_buckets()
    sin_vencidas = 0
    hoy = hoy_negocio()

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
        "segmentacion": "dashboard_menu",
    }
    pids = [int(p.id) for p in prestamos]
    pid_to_cliente: dict[int, Optional[int]] = {}
    prestamo_by_id: dict[int, Prestamo] = {}
    for p in prestamos:
        pid_to_cliente[int(p.id)] = int(p.cliente_id) if p.cliente_id is not None else None
        prestamo_by_id[int(p.id)] = p

    by_pid: dict[int, list[Cuota]] = defaultdict(list)
    cuota_ids: list[int] = []
    if pids:
        for c in db.query(Cuota).filter(Cuota.prestamo_id.in_(pids)).all():
            by_pid[int(c.prestamo_id)].append(c)
            cuota_ids.append(int(c.id))

    z = ZoneInfo(TZ_NEGOCIO)
    eventos_por_cuota = _load_eventos_por_cuota(db, cuota_ids, z)

    montos_snap: dict[str, Decimal] = {k: Decimal("0") for k in _BUCKET_KEYS}
    cant_snap: dict[str, int] = {k: 0 for k in _BUCKET_KEYS}

    filas_hoy: list[tuple[int, Optional[int], str, float]] = []
    cuotas_atrasadas_hoy: dict[int, int] = {}
    for pid in pids:
        bucket, saldo, dias = _metricas_prestamo_en_fecha(
            by_pid.get(pid, []), eventos_por_cuota, hoy, hoy
        )
        if not dias:
            sin_vencidas += 1
            continue
        cuotas_atrasadas_hoy[pid] = len(dias)
        if not bucket:
            continue
        filas_hoy.append((pid, pid_to_cliente.get(pid), bucket, float(saldo)))

    for pid, _cid, bucket, saldo_r in _aplicar_exclusion_cliente_bucket_1(filas_hoy):
        p = prestamo_by_id[pid]
        item = {
            "prestamo_id": pid,
            "cedula": p.cedula or "",
            "nombres": p.nombres,
            "cuotas_vencidas": int(cuotas_atrasadas_hoy.get(pid, 0)),
            "saldo_vencido_usd": float(saldo_r),
        }
        buckets[bucket]["items"].append(item)
        buckets[bucket]["cantidad"] += 1
        buckets[bucket]["monto_usd"] = round(
            float(buckets[bucket]["monto_usd"]) + float(saldo_r), 2
        )
        montos_snap[bucket] += Decimal(str(saldo_r))
        cant_snap[bucket] += 1

    _upsert_snapshot_hoy(db, hoy, montos_snap, cant_snap)

    serie = _serie_diaria_30_desde_universo(
        pids, by_pid, eventos_por_cuota, pid_to_cliente, hoy
    )

    meta["cantidad"] = len(prestamos)
    return {
        "buckets": buckets,
        "sin_vencidas": sin_vencidas,
        "serie_diaria": serie,
        "desempeno_lecturas": _lecturas_lunes_desempeno(
            pids, by_pid, eventos_por_cuota, pid_to_cliente, hoy
        ),
        "meta": meta,
    }
