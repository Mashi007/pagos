"""Analisis del universo de cedulas Excel para cobranzas."""

from __future__ import annotations

import io
import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional, Sequence

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.cobranza_universo import CobranzaUniversoCedula, CobranzaUniversoDesempenoDiario
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.services.cuota_estado import (
    clasificar_estado_cuota,
    dias_retraso_desde_vencimiento,
    hoy_negocio,
)
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    normalizar_cedula_almacenamiento,
    texto_cedula_comparable_bd,
)

logger = logging.getLogger(__name__)

_HEADER_CELLS = frozenset({"cedula", "cedulas", "documento", "id"})
_BUCKET_KEYS = ("1", "2", "3", "4plus")


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
    """True si no hay universo cargado o la cedula esta en la lista."""
    if contar_universo(db) == 0:
        return True
    key = texto_cedula_comparable_bd(cedula_raw)
    if not key:
        return False
    return key in claves_universo(db)


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
    if n_vencidas <= 0:
        return None
    if n_vencidas == 1:
        return "1"
    if n_vencidas == 2:
        return "2"
    if n_vencidas == 3:
        return "3"
    return "4plus"


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


def _cuota_vencida_saldo_en_fecha(
    monto: float,
    total_pagado: float,
    fecha_vencimiento: date | None,
    fecha_pago: date | None,
    dia: date,
    es_hoy: bool,
) -> Optional[float]:
    """Saldo de cuota vencida en `dia`, o None si no cuenta ese dia."""
    if fecha_pago is not None and fecha_pago <= dia:
        return None
    if dias_retraso_desde_vencimiento(fecha_vencimiento, dia) < 1:
        return None
    if es_hoy:
        estado = clasificar_estado_cuota(total_pagado, monto, fecha_vencimiento, dia)
        if estado in ("PAGADO", "PAGO_ADELANTADO"):
            return None
        return max(0.0, float(monto) - float(total_pagado or 0))
    # Historico: pago despues de `dia` implica que la cuota completa se debia ese dia.
    return max(0.0, float(monto or 0))


def _buckets_metricas_en_fecha(
    prestamo_ids: Sequence[int],
    by_pid: dict[int, list[Cuota]],
    dia: date,
    hoy: date,
) -> tuple[dict[str, float], dict[str, int]]:
    """Montos USD y cantidad de prestamos por bucket (1/2/3/4plus) en `dia`."""
    montos: dict[str, float] = {k: 0.0 for k in _BUCKET_KEYS}
    cants: dict[str, int] = {k: 0 for k in _BUCKET_KEYS}
    es_hoy = dia == hoy
    for pid in prestamo_ids:
        n_venc = 0
        saldo = 0.0
        for c in by_pid.get(pid, []):
            monto = float(c.monto or 0)
            paid = float(c.total_pagado or 0)
            s = _cuota_vencida_saldo_en_fecha(
                monto,
                paid,
                c.fecha_vencimiento,
                c.fecha_pago,
                dia,
                es_hoy,
            )
            if s is None:
                continue
            n_venc += 1
            saldo += s
        b = _bucket_clave(n_venc)
        if not b:
            continue
        montos[b] = round(montos[b] + round(saldo, 2), 2)
        cants[b] += 1
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
    hoy: date,
) -> list[dict[str, Any]]:
    """Reconstruye 30 dias (hoy-29..hoy): montos USD y cantidad de prestamos."""
    serie: list[dict[str, Any]] = []
    for i in range(30):
        dia = hoy - timedelta(days=29 - i)
        montos, cants = _buckets_metricas_en_fecha(prestamo_ids, by_pid, dia, hoy)
        serie.append(_punto_serie_desde_metricas(dia, montos, cants))
    return serie


def _pct_var(actual: float, base: float) -> Optional[float]:
    if abs(base) < 0.005:
        if abs(actual) < 0.005:
            return 0.0
        return None
    return round(((actual - base) / abs(base)) * 100.0, 2)


def _fechas_4_lunes_mas_hoy(hoy: date) -> list[date]:
    """4 lunes anteriores a hoy (estrictamente) + hoy. Siempre 5 fechas distintas."""
    cursor = hoy - timedelta(days=1)
    while cursor.weekday() != 0:  # lunes = 0
        cursor -= timedelta(days=1)
    lunes: list[date] = []
    for _ in range(4):
        lunes.append(cursor)
        cursor -= timedelta(days=7)
    lunes.reverse()
    return lunes + [hoy]


def _etiqueta_lectura(d: date, hoy: date) -> str:
    dd = d.strftime("%d/%m")
    if d == hoy:
        return f"Hoy {dd}"
    if d.weekday() == 0:
        return f"Lun {dd}"
    return dd


def _lecturas_lunes_desempeno(
    prestamo_ids: Sequence[int],
    by_pid: dict[int, list[Cuota]],
    hoy: date,
) -> dict[str, Any]:
    """Cantidades y montos por bucket en 4 lunes previos + hoy. Sin deltas."""
    fechas = _fechas_4_lunes_mas_hoy(hoy)
    snaps: list[tuple[date, dict[str, float], dict[str, int]]] = []
    for dia in fechas:
        montos, cants = _buckets_metricas_en_fecha(prestamo_ids, by_pid, dia, hoy)
        snaps.append((dia, montos, cants))

    columnas = [
        {
            "fecha": dia.isoformat(),
            "etiqueta": _etiqueta_lectura(dia, hoy),
            "es_hoy": dia == hoy,
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
    """Buckets por cuotas vencidas de prestamos APROBADO en el universo; upsert snapshot del dia."""
    buckets = _empty_buckets()
    sin_vencidas = 0
    meta = meta_universo(db)
    claves = claves_universo(db)
    hoy = hoy_negocio()

    if not claves:
        serie_vacia = _serie_diaria_30_vacia(hoy)
        return {
            "buckets": buckets,
            "sin_vencidas": 0,
            "serie_diaria": serie_vacia,
            "desempeno_lecturas": _lecturas_lunes_desempeno([], {}, hoy),
            "meta": meta,
        }

    prestamos = (
        db.query(Prestamo)
        .filter(
            Prestamo.estado == "APROBADO",
            expr_cedula_normalizada_para_comparar(Prestamo.cedula).in_(list(claves)),
        )
        .all()
    )
    pids = [p.id for p in prestamos]
    by_pid: dict[int, list[Cuota]] = defaultdict(list)
    if pids:
        for c in db.query(Cuota).filter(Cuota.prestamo_id.in_(pids)).all():
            by_pid[c.prestamo_id].append(c)

    montos_snap: dict[str, Decimal] = {k: Decimal("0") for k in _BUCKET_KEYS}
    cant_snap: dict[str, int] = {k: 0 for k in _BUCKET_KEYS}

    for p in prestamos:
        n_venc = 0
        saldo = 0.0
        for c in by_pid.get(p.id, []):
            monto = float(c.monto or 0)
            paid = float(c.total_pagado or 0)
            fv = c.fecha_vencimiento
            estado = clasificar_estado_cuota(paid, monto, fv, hoy)
            if estado in ("PAGADO", "PAGO_ADELANTADO"):
                continue
            if dias_retraso_desde_vencimiento(fv, hoy) < 1:
                continue
            n_venc += 1
            saldo += max(0.0, monto - paid)

        if n_venc == 0:
            sin_vencidas += 1
            continue

        b = _bucket_clave(n_venc)
        if not b:
            continue
        saldo_r = round(saldo, 2)
        item = {
            "prestamo_id": p.id,
            "cedula": p.cedula or "",
            "nombres": p.nombres,
            "cuotas_vencidas": n_venc,
            "saldo_vencido_usd": saldo_r,
        }
        buckets[b]["items"].append(item)
        buckets[b]["cantidad"] += 1
        buckets[b]["monto_usd"] = round(
            float(buckets[b]["monto_usd"]) + saldo_r, 2
        )
        montos_snap[b] += Decimal(str(saldo_r))
        cant_snap[b] += 1

    _upsert_snapshot_hoy(db, hoy, montos_snap, cant_snap)

    serie = _serie_diaria_30_desde_universo(pids, by_pid, hoy)

    return {
        "buckets": buckets,
        "sin_vencidas": sin_vencidas,
        "serie_diaria": serie,
        "desempeno_lecturas": _lecturas_lunes_desempeno(pids, by_pid, hoy),
        "meta": meta_universo(db),
    }
