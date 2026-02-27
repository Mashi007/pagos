"""
Reportes contables (con cache).
"""
import calendar
import io
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import func, select, and_, or_, delete
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.reporte_contable_cache import ReporteContableCache

from app.api.v1.endpoints.reportes_utils import _safe_float

router = APIRouter(dependencies=[Depends(get_current_user)])

CONTABLE_CACHE_DIAS_ACTUALIZABLES = 7


def _obtener_tasa_usd_bs(fecha: date) -> float:
    """Obtiene tasa USD a BolÃ­vares (Venezuela) para la fecha."""
    from app.core.config import settings
    import urllib.request
    import json

    if settings.TASA_USD_BS_DEFAULT is not None and fecha < date.today():
        return float(settings.TASA_USD_BS_DEFAULT)

    try:
        req = urllib.request.Request(
            settings.EXCHANGERATE_API_URL,
            headers={"User-Agent": "RapiCredit/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        rates = data.get("rates", {})
        tasa = rates.get("VES")
        if tasa is not None:
            return float(tasa)
    except Exception:
        pass

    if settings.TASA_USD_BS_DEFAULT is not None:
        return float(settings.TASA_USD_BS_DEFAULT)
    return 36.0


def _cuotas_a_filas_contable(rows, tasas_cache: dict) -> List[dict]:
    """Convierte filas a formato contable. Fecha de pago e Importe MD salen de tabla pagos cuando existe."""
    items: List[dict] = []
    for r in rows:
        # Fecha de pago: tabla pagos (fecha_pago_real) o fallback Cuota.fecha_pago
        fp = getattr(r, "fecha_pago_real", None) or r.fecha_pago
        fp_date = fp.date() if hasattr(fp, "date") else (date.fromisoformat(str(fp)[:10]) if fp else date.today())
        if fp_date not in tasas_cache:
            tasas_cache[fp_date] = _obtener_tasa_usd_bs(fp_date)
        tasa = tasas_cache[fp_date]

        monto_cuota = _safe_float(r.monto)
        # Importe MD: tabla pagos (monto_pagado_real) o fallback Cuota.total_pagado / Cuota.monto
        monto_pago_real = getattr(r, "monto_pagado_real", None)
        if monto_pago_real is not None:
            total_pagado = _safe_float(monto_pago_real)
        else:
            total_pagado_raw = _safe_float(getattr(r, "total_pagado", None))
            total_pagado = total_pagado_raw if total_pagado_raw > 0 else monto_cuota
        pago_completo = total_pagado >= monto_cuota - 0.01
        tipo_doc = f"Cuota {r.numero_cuota}" if pago_completo else "Abono"
        importe_ml = round(total_pagado * tasa, 2)

        items.append({
            "cuota_id": r.id,
            "cedula": r.cedula or "",
            "nombre": (r.nombres or "").strip(),
            "tipo_documento": tipo_doc,
            "fecha_vencimiento": r.fecha_vencimiento,
            "fecha_pago": fp_date,
            "importe_md": round(total_pagado, 2),
            "moneda_documento": "USD",
            "tasa": tasa,
            "importe_ml": importe_ml,
            "moneda_local": "Bs.",
        })
    return items

def _cuotas_a_filas_contable_con_signo(rows, tasas_cache: dict) -> List[dict]:
    """Todas las cuotas: con pago en tabla pagos -> Importe MD positivo; sin pago -> negativo (no pago)."""
    items: List[dict] = []
    for r in rows:
        monto_cuota = _safe_float(r.monto)
        monto_pago_real = getattr(r, "monto_pagado_real", None)
        try:
            tiene_pago = monto_pago_real is not None and _safe_float(monto_pago_real) > 0
        except (TypeError, ValueError):
            tiene_pago = False

        if tiene_pago:
            importe_md = round(_safe_float(monto_pago_real), 2)
            fp = getattr(r, "fecha_pago_real", None) or r.fecha_pago
            fp_date = fp.date() if hasattr(fp, "date") else (date.fromisoformat(str(fp)[:10]) if fp else None)
            tipo_doc = f"Cuota {r.numero_cuota}"
            fecha_pago_text = None
        else:
            fv = r.fecha_vencimiento
            por_vencer = fv >= date.today()
            if por_vencer:
                importe_md = round(monto_cuota, 2)
                fp_date = None
                fecha_pago_text = "POR VENCER"
            else:
                importe_md = round(-monto_cuota, 2)
                fp_date = None
                fecha_pago_text = "no pago"
            tipo_doc = f"Cuota {r.numero_cuota}"

        fv = r.fecha_vencimiento
        if fp_date is not None:
            if fp_date not in tasas_cache:
                tasas_cache[fp_date] = _obtener_tasa_usd_bs(fp_date)
            tasa = tasas_cache[fp_date]
        else:
            if fv not in tasas_cache:
                tasas_cache[fv] = _obtener_tasa_usd_bs(fv)
            tasa = tasas_cache[fv]
        importe_ml = round(importe_md * tasa, 2)
        fa = getattr(r, "fecha_aprobacion", None)
        fa_str = fa.date().isoformat() if fa and hasattr(fa, "date") else (fa.isoformat()[:10] if fa else "-")

        items.append({
            "cuota_id": r.id,
            "cedula": r.cedula or "",
            "nombre": (r.nombres or "").strip(),
            "tipo_documento": tipo_doc,
            "fecha_aprobacion_prestamo": fa_str,
            "fecha_vencimiento": fv,
            "fecha_pago": fp_date,
            "fecha_pago_text": fecha_pago_text,
            "importe_md": importe_md,
            "moneda_documento": "USD",
            "tasa": tasa,
            "importe_ml": importe_ml,
            "moneda_local": "Bs.",
        })
    return items


def _query_cuotas_contable(db: Session, fecha_inicio: date, fecha_fin: date):
    """Consulta cuotas con pago en el rango dado. Incluye todos los pagos (no filtra por ACTIVO/APROBADO).
    Usa Cuota.fecha_pago o, si existe, Pago.fecha_pago como fecha de pago efectiva.
    Excluye prestamos null: solo incluye cuotas con prestamo_id y prestamo valido (Prestamo.id no null)."""
    prestamo_valido = and_(Cuota.prestamo_id.isnot(None), Prestamo.id.isnot(None))
    rango_cuota = and_(
        Cuota.fecha_pago.isnot(None),
        Cuota.fecha_pago >= fecha_inicio,
        Cuota.fecha_pago <= fecha_fin,
    )
    if hasattr(Cuota, "pago_id") and hasattr(Cuota, "total_pagado"):
        rango_pago = and_(
            Pago.fecha_pago.isnot(None),
            Pago.fecha_pago >= fecha_inicio,
            Pago.fecha_pago <= fecha_fin,
        )
        where_rango = or_(rango_cuota, rango_pago)
        q = (
            select(
                Cuota.id,
                Cuota.numero_cuota,
                Cuota.fecha_vencimiento,
                Cuota.fecha_pago,
                Cuota.monto,
                Cuota.total_pagado,
                Prestamo.cedula,
                Prestamo.nombres,
                Pago.fecha_pago.label("fecha_pago_real"),
                Pago.monto_pagado.label("monto_pagado_real"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .outerjoin(Pago, Cuota.pago_id == Pago.id)
            .where(and_(prestamo_valido, where_rango))
        )
    else:
        q = (
            select(
                Cuota.id,
                Cuota.numero_cuota,
                Cuota.fecha_vencimiento,
                Cuota.fecha_pago,
                Cuota.monto,
                Cuota.monto.label("total_pagado"),
                Prestamo.cedula,
                Prestamo.nombres,
                Cuota.fecha_pago.label("fecha_pago_real"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .where(and_(prestamo_valido, rango_cuota))
        )
    return db.execute(q).fetchall()


def _query_cuotas_por_vencimiento(db: Session, fecha_inicio: date, fecha_fin: date):
    """Todas las cuotas con fecha_vencimiento en el rango (incl. pagadas, vencidas sin pago y futuras). LEFT JOIN pagos. No se filtra por date.today()."""
    prestamo_valido = and_(Cuota.prestamo_id.isnot(None), Prestamo.id.isnot(None))
    rango_vencimiento = and_(
        Cuota.fecha_vencimiento >= fecha_inicio,
        Cuota.fecha_vencimiento <= fecha_fin,
    )
    if hasattr(Cuota, "pago_id"):
        q = (
            select(
                Cuota.id, Cuota.numero_cuota, Cuota.fecha_vencimiento, Cuota.fecha_pago,
                Cuota.monto, Cuota.total_pagado, Prestamo.cedula, Prestamo.nombres,
                Prestamo.fecha_aprobacion,
                Pago.fecha_pago.label("fecha_pago_real"), Pago.monto_pagado.label("monto_pagado_real"),
            )
            .select_from(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .outerjoin(Pago, Cuota.pago_id == Pago.id)
            .where(and_(prestamo_valido, rango_vencimiento))
        )
    else:
        q = (
            select(
                Cuota.id, Cuota.numero_cuota, Cuota.fecha_vencimiento, Cuota.fecha_pago,
                Cuota.monto, Cuota.monto.label("total_pagado"), Prestamo.cedula, Prestamo.nombres,
                Prestamo.fecha_aprobacion,
                Cuota.fecha_pago.label("fecha_pago_real"),
            )
            .select_from(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .where(and_(prestamo_valido, rango_vencimiento))
        )
    return db.execute(q).fetchall()


def sync_reporte_contable_completo(db: Session) -> int:
    """Sincroniza todo el histÃ³rico al cache. Retorna cantidad de filas insertadas."""
    fi = date(2000, 1, 1)
    ff = date.today()
    rows = _query_cuotas_contable(db, fi, ff)
    tasas: dict = {}
    filas = _cuotas_a_filas_contable(rows, tasas)

    existentes = set(
        r[0] for r in db.execute(select(ReporteContableCache.cuota_id)).fetchall()
    )
    insertadas = 0
    for f in filas:
        if f["cuota_id"] not in existentes:
            db.add(ReporteContableCache(
                cuota_id=f["cuota_id"],
                cedula=f["cedula"],
                nombre=f["nombre"],
                tipo_documento=f["tipo_documento"],
                fecha_vencimiento=f["fecha_vencimiento"],
                fecha_pago=f["fecha_pago"],
                importe_md=f["importe_md"],
                moneda_documento=f["moneda_documento"],
                tasa=f["tasa"],
                importe_ml=f["importe_ml"],
                moneda_local=f["moneda_local"],
            ))
            insertadas += 1
    if insertadas:
        db.commit()
    return insertadas


def refresh_cache_ultimos_7_dias(db: Session) -> int:
    """Elimina y reinserta en cache solo los ultimos 7 dias. Deduplica por cuota_id y borra por cuota_id para evitar UniqueViolation."""
    hoy = date.today()
    limite = hoy - timedelta(days=CONTABLE_CACHE_DIAS_ACTUALIZABLES)

    rows = _query_cuotas_contable(db, limite, hoy)
    tasas: dict = {}
    filas = _cuotas_a_filas_contable(rows, tasas)
    # Deduplicate by cuota_id (keep last) in case the query returns duplicates
    by_cuota: dict = {f["cuota_id"]: f for f in filas}
    filas = list(by_cuota.values())

    if filas:
        cuota_ids = [f["cuota_id"] for f in filas]
        db.execute(delete(ReporteContableCache).where(ReporteContableCache.cuota_id.in_(cuota_ids)))
        db.commit()
        for f in filas:
            db.add(ReporteContableCache(
                cuota_id=f["cuota_id"],
                cedula=f["cedula"],
                nombre=f["nombre"],
                tipo_documento=f["tipo_documento"],
                fecha_vencimiento=f["fecha_vencimiento"],
                fecha_pago=f["fecha_pago"],
                importe_md=f["importe_md"],
                moneda_documento=f["moneda_documento"],
                tasa=f["tasa"],
                importe_ml=f["importe_ml"],
                moneda_local=f["moneda_local"],
            ))
        db.commit()
    return len(filas)

def get_reporte_contable_desde_cache(
    db: Session,
    anos: List[int],
    meses: List[int],
    cedulas: Optional[List[str]] = None,
) -> dict:
    """Lee del cache filtrando por aÃ±os, meses y opcionalmente cÃ©dulas."""
    if not anos or not meses:
        return {"items": [], "fecha_inicio": "", "fecha_fin": ""}

    periodos = [(a, m) for a in anos for m in meses]
    if not periodos:
        return {"items": [], "fecha_inicio": "", "fecha_fin": ""}

    condiciones = []
    for ano, mes in periodos:
        _, ultimo = calendar.monthrange(ano, mes)
        inicio = date(ano, mes, 1)
        fin = date(ano, mes, ultimo)
        condiciones.append(and_(ReporteContableCache.fecha_pago >= inicio, ReporteContableCache.fecha_pago <= fin))

    # Seleccion por columnas explicitas: una fila por cuota, sin colapsar por ORM/identidad
    q = (
        select(
            ReporteContableCache.cedula,
            ReporteContableCache.nombre,
            ReporteContableCache.tipo_documento,
            ReporteContableCache.fecha_vencimiento,
            ReporteContableCache.fecha_pago,
            ReporteContableCache.importe_md,
            ReporteContableCache.moneda_documento,
            ReporteContableCache.tasa,
            ReporteContableCache.importe_ml,
            ReporteContableCache.moneda_local,
        )
        .where(or_(*condiciones) if len(condiciones) > 1 else condiciones[0])
        .order_by(
            ReporteContableCache.fecha_pago.asc(),
            ReporteContableCache.cedula.asc(),
            ReporteContableCache.cuota_id.asc(),
        )
    )
    if cedulas:
        q = q.where(ReporteContableCache.cedula.in_(cedulas))

    rows = db.execute(q).fetchall()
    items = [
        {
            "cedula": row[0] or "",
            "nombre": (row[1] or "").strip(),
            "tipo_documento": row[2] or "",
            "fecha_vencimiento": row[3].isoformat() if row[3] else "",
            "fecha_pago": row[4].isoformat() if row[4] else "",
            "importe_md": _safe_float(row[5]),
            "moneda_documento": row[6] or "USD",
            "tasa": _safe_float(row[7]),
            "importe_ml": _safe_float(row[8]),
            "moneda_local": row[9] or "Bs.",
        }
        for row in rows
    ]

    min_periodo = min(periodos, key=lambda p: (p[0], p[1]))
    max_periodo = max(periodos, key=lambda p: (p[0], p[1]))
    fi = date(min_periodo[0], min_periodo[1], 1)
    _, ult = calendar.monthrange(max_periodo[0], max_periodo[1])
    ff = date(max_periodo[0], max_periodo[1], ult)

    return {"items": items, "fecha_inicio": fi.isoformat(), "fecha_fin": ff.isoformat()}


def _generar_excel_contable(data: dict) -> bytes:
    """Genera Excel reporte contable."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte Contable"
    items = data.get("items", [])
    ws.append(["Reporte Contable"])
    ws.append([f"PerÃ­odo: {data.get('fecha_inicio', '')} a {data.get('fecha_fin', '')}"])
    ws.append([])
    headers = [
        "CÃ©dula", "Nombre", "Tipo de documento", "Fecha de vencimiento", "Fecha de pago",
        "Importe MD", "Moneda documento", "Tasa", "Importe en ML", "Moneda Local",
    ]
    ws.append(headers)
    if items:
        for r in items:
            ws.append([
                r.get("cedula", ""), r.get("nombre", ""), r.get("tipo_documento", ""),
                r.get("fecha_aprobacion_prestamo", ""),
                r.get("fecha_vencimiento", ""), r.get("fecha_pago", ""),
                r.get("importe_md", 0), r.get("moneda_documento", "USD"),
                r.get("tasa", 0), r.get("importe_ml", 0), r.get("moneda_local", "Bs."),
            ])
    else:
        ws.append(["(Sin datos)"])
        ws.append([
            "No hay cuotas pagadas en el perÃ­odo seleccionado. "
            "Verifique: 1) Que las fechas sean pasadas (no futuras). 2) Que existan cuotas con fecha de pago en ese mes.",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/contable/cedulas")
def buscar_cedulas_contable(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="BÃºsqueda por cÃ©dula o nombre"),
    limit: int = Query(50, ge=1, le=200),
):
    """Busca cÃ©dulas para filtrar reporte contable."""
    try:
        ReporteContableCache.__table__.create(db.get_bind(), checkfirst=True)
    except Exception:
        pass

    count_cache = db.scalar(select(func.count()).select_from(ReporteContableCache)) or 0
    if count_cache > 0:
        subq = select(ReporteContableCache.cedula, ReporteContableCache.nombre).distinct()
        if q and q.strip():
            term = f"%{q.strip()}%"
            subq = subq.where(
                or_(
                    ReporteContableCache.cedula.ilike(term),
                    ReporteContableCache.nombre.ilike(term),
                )
            )
        rows = db.execute(subq.limit(limit)).fetchall()
    else:
        subq = (
            select(Prestamo.cedula, Prestamo.nombres)
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.isnot(None),
            )
            .distinct()
        )
        try:
            subq = subq.where(Cuota.total_pagado.isnot(None), Cuota.total_pagado > 0)
        except AttributeError:
            pass
        if q and q.strip():
            term = f"%{q.strip()}%"
            subq = subq.where(or_(Prestamo.cedula.ilike(term), Prestamo.nombres.ilike(term)))
        rows = db.execute(subq.limit(limit)).fetchall()
    return {"cedulas": [{"cedula": r[0] or "", "nombre": (r[1] or "").strip()} for r in rows]}


@router.get("/exportar/contable")
def exportar_contable(
    request: Request,
    db: Session = Depends(get_db),
    anos: Optional[str] = Query(None, description="AÃ±os separados por coma, ej. 2024,2025"),
    meses: Optional[str] = Query(None, description="Meses 1-12 separados por coma, ej. 1,6,12"),
    cedulas: Optional[str] = Query(None, description="CÃ©dulas separadas por coma (vacÃ­o = todas)"),
):
    """Exporta reporte contable en Excel desde cache."""
    if anos is None:
        anos = request.query_params.get("anos") or request.query_params.get("aÃ±os")
    try:
        ReporteContableCache.__table__.create(db.get_bind(), checkfirst=True)
    except Exception:
        pass

    count_cache = db.scalar(select(func.count()).select_from(ReporteContableCache)) or 0
    if count_cache == 0:
        sync_reporte_contable_completo(db)
    else:
        refresh_cache_ultimos_7_dias(db)

    anos_list = []
    if anos:
        try:
            anos_list = sorted([int(x.strip()) for x in anos.split(",") if x.strip()], reverse=True)
        except (ValueError, TypeError):
            anos_list = [date.today().year]
    if not anos_list:
        anos_list = [date.today().year]

    meses_list = []
    if meses:
        try:
            meses_list = sorted([int(x.strip()) for x in meses.split(",") if x.strip() and 1 <= int(x.strip()) <= 12])
        except (ValueError, TypeError):
            meses_list = list(range(1, 13))
    if not meses_list:
        meses_list = list(range(1, 13))

    cedulas_list = None
    if cedulas and cedulas.strip():
        cedulas_list = [c.strip() for c in cedulas.split(",") if c.strip()]

    # Todas las cuotas con vencimiento en el periodo (pagadas, vencidas y futuras): con pago -> Importe MD +; sin pago -> -
    periodos = [(a, m) for a in anos_list for m in meses_list]
    if not periodos:
        data = {"items": [], "fecha_inicio": "", "fecha_fin": ""}
    else:
        min_p = min(periodos, key=lambda p: (p[0], p[1]))
        max_p = max(periodos, key=lambda p: (p[0], p[1]))
        fi = date(min_p[0], min_p[1], 1)
        _, ult = calendar.monthrange(max_p[0], max_p[1])
        ff = date(max_p[0], max_p[1], ult)
        rows = _query_cuotas_por_vencimiento(db, fi, ff)
        tasas_fb = {}
        filas_fb = _cuotas_a_filas_contable_con_signo(rows, tasas_fb)
        if cedulas_list:
            filas_fb = [f for f in filas_fb if f["cedula"] in cedulas_list]
        items = []
        for f in filas_fb:
            fv = f.get("fecha_vencimiento")
            fp = f.get("fecha_pago")
            items.append({
                "cedula": f["cedula"],
                "nombre": f["nombre"],
                "tipo_documento": f["tipo_documento"],
                "fecha_aprobacion_prestamo": f.get("fecha_aprobacion_prestamo", ""),
                "fecha_vencimiento": fv.isoformat() if hasattr(fv, "isoformat") else str(fv or ""),
                "fecha_pago": fp.isoformat() if fp and hasattr(fp, "isoformat") else (f.get("fecha_pago_text") or "no pago"),
                "importe_md": _safe_float(f.get("importe_md")),
                "moneda_documento": f.get("moneda_documento") or "USD",
                "tasa": _safe_float(f.get("tasa")),
                "importe_ml": _safe_float(f.get("importe_ml")),
                "moneda_local": f.get("moneda_local") or "Bs.",
            })
        data = {"items": items, "fecha_inicio": fi.isoformat(), "fecha_fin": ff.isoformat()}
    content = _generar_excel_contable(data)
    hoy_str = date.today().isoformat()
    headers = {"Content-Disposition": f"attachment; filename=reporte_contable_{hoy_str}.xlsx"}
    if not data.get("items", []):
        headers["X-Reporte-Contable-Vacio"] = "1"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
