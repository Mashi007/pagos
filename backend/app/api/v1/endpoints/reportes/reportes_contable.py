"""
Reportes contables (con cache).
"""
import calendar
import io
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
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
    """Obtiene tasa USD a Bolívares (Venezuela) para la fecha."""
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
    """Convierte filas de cuotas a formato contable con tasa guardada."""
    items: List[dict] = []
    for r in rows:
        fp = getattr(r, "fecha_pago_real", None) or r.fecha_pago
        fp_date = fp.date() if hasattr(fp, "date") else (date.fromisoformat(str(fp)[:10]) if fp else date.today())
        if fp_date not in tasas_cache:
            tasas_cache[fp_date] = _obtener_tasa_usd_bs(fp_date)
        tasa = tasas_cache[fp_date]

        monto_cuota = _safe_float(r.monto)
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


def _query_cuotas_contable(db: Session, fecha_inicio: date, fecha_fin: date):
    """Consulta cuotas con pago en el rango dado."""
    q = (
        select(
            Cuota.id,
            Cuota.numero_cuota,
            Cuota.fecha_vencimiento,
            Cuota.fecha_pago,
            Cuota.monto,
            Cuota.total_pagado if hasattr(Cuota, "total_pagado") else Cuota.monto,
            Prestamo.cedula,
            Prestamo.nombres,
            Pago.fecha_pago.label("fecha_pago_real"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .outerjoin(Pago, Cuota.pago_id == Pago.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.isnot(None),
            Cuota.fecha_pago >= fecha_inicio,
            Cuota.fecha_pago <= fecha_fin,
        )
    )
    return db.execute(q).fetchall()


def sync_reporte_contable_completo(db: Session) -> int:
    """Sincroniza todo el histórico al cache. Retorna cantidad de filas insertadas."""
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
    """Elimina y reinserta en cache solo los últimos 7 días."""
    hoy = date.today()
    limite = hoy - timedelta(days=CONTABLE_CACHE_DIAS_ACTUALIZABLES)

    db.execute(delete(ReporteContableCache).where(ReporteContableCache.fecha_pago >= limite))
    db.commit()

    rows = _query_cuotas_contable(db, limite, hoy)
    tasas: dict = {}
    filas = _cuotas_a_filas_contable(rows, tasas)

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
    """Lee del cache filtrando por años, meses y opcionalmente cédulas."""
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

    q = (
        select(ReporteContableCache)
        .where(or_(*condiciones) if len(condiciones) > 1 else condiciones[0])
        .order_by(ReporteContableCache.fecha_pago.asc(), ReporteContableCache.cedula.asc())
    )
    if cedulas:
        q = q.where(ReporteContableCache.cedula.in_(cedulas))

    rows = db.execute(q).scalars().all()
    items = [
        {
            "cedula": r.cedula,
            "nombre": r.nombre,
            "tipo_documento": r.tipo_documento,
            "fecha_vencimiento": r.fecha_vencimiento.isoformat() if r.fecha_vencimiento else "",
            "fecha_pago": r.fecha_pago.isoformat() if r.fecha_pago else "",
            "importe_md": _safe_float(r.importe_md),
            "moneda_documento": r.moneda_documento or "USD",
            "tasa": _safe_float(r.tasa),
            "importe_ml": _safe_float(r.importe_ml),
            "moneda_local": r.moneda_local or "Bs.",
        }
        for r in rows
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
    ws.append([f"Período: {data.get('fecha_inicio', '')} a {data.get('fecha_fin', '')}"])
    ws.append([])
    headers = [
        "Cédula", "Nombre", "Tipo de documento", "Fecha de vencimiento", "Fecha de pago",
        "Importe MD", "Moneda documento", "Tasa", "Importe en ML", "Moneda Local",
    ]
    ws.append(headers)
    for r in items:
        ws.append([
            r.get("cedula", ""), r.get("nombre", ""), r.get("tipo_documento", ""),
            r.get("fecha_vencimiento", ""), r.get("fecha_pago", ""),
            r.get("importe_md", 0), r.get("moneda_documento", "USD"),
            r.get("tasa", 0), r.get("importe_ml", 0), r.get("moneda_local", "Bs."),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/contable/cedulas")
def buscar_cedulas_contable(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Búsqueda por cédula o nombre"),
    limit: int = Query(50, ge=1, le=200),
):
    """Busca cédulas para filtrar reporte contable."""
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
        if hasattr(Cuota, "total_pagado"):
            subq = subq.where(Cuota.total_pagado.isnot(None), Cuota.total_pagado > 0)
        if q and q.strip():
            term = f"%{q.strip()}%"
            subq = subq.where(or_(Prestamo.cedula.ilike(term), Prestamo.nombres.ilike(term)))
        rows = db.execute(subq.limit(limit)).fetchall()
    return {"cedulas": [{"cedula": r[0] or "", "nombre": (r[1] or "").strip()} for r in rows]}


@router.get("/exportar/contable")
def exportar_contable(
    db: Session = Depends(get_db),
    anos: Optional[str] = Query(None, description="Años separados por coma, ej. 2024,2025"),
    meses: Optional[str] = Query(None, description="Meses 1-12 separados por coma, ej. 1,6,12"),
    cedulas: Optional[str] = Query(None, description="Cédulas separadas por coma (vacío = todas)"),
):
    """Exporta reporte contable en Excel desde cache."""
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

    data = get_reporte_contable_desde_cache(db, anos=anos_list, meses=meses_list, cedulas=cedulas_list)
    content = _generar_excel_contable(data)
    hoy_str = date.today().isoformat()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reporte_contable_{hoy_str}.xlsx"},
    )
