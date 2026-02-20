"""
Reportes por asesores/analistas.
"""
import calendar
import io
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

from app.api.v1.endpoints.reportes_utils import _safe_float, _parse_fecha, _periodos_desde_filtros

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/asesores/por-mes")
def get_asesores_por_mes(
    db: Session = Depends(get_db),
    meses: int = Query(12, ge=1, le=24, description="Cantidad de meses hacia atrás"),
    anos: Optional[str] = Query(None),
    meses_list: Optional[str] = Query(None),
):
    """Asesores por mes: una pestaña por mes. Solo cuotas con fecha_vencimiento en el mes y sin pagar."""
    resultado: dict = {"meses": []}
    periodos = _periodos_desde_filtros(anos, meses_list, meses)

    for (ano, mes) in periodos:
        inicio = date(ano, mes, 1)
        _, ultimo = calendar.monthrange(ano, mes)
        fin = date(ano, mes, ultimo)

        rows = db.execute(
            select(
                Prestamo.analista,
                func.coalesce(func.sum(Cuota.monto), 0).label("vencimiento_total"),
                func.count(func.distinct(Cuota.prestamo_id)).label("total_prestamos"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento >= inicio,
                Cuota.fecha_vencimiento <= fin,
            )
            .group_by(Prestamo.analista)
            .order_by(func.sum(Cuota.monto).desc())
        ).fetchall()

        items = [
            {
                "analista": r.analista or "Sin asignar",
                "vencimiento_total": round(_safe_float(r.vencimiento_total), 2),
                "total_prestamos": r.total_prestamos or 0,
            }
            for r in rows
        ]

        resultado["meses"].append({
            "mes": mes,
            "ano": ano,
            "label": f"{mes:02d}/{ano}",
            "items": items,
        })

    return resultado


@router.get("/asesores")
def get_reporte_asesores(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None),
):
    """Reporte por asesor/analista. Datos reales desde BD (solo clientes ACTIVOS)."""
    fc = _parse_fecha(fecha_corte)
    analistas = db.execute(
        select(Prestamo.analista)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO")
        .distinct()
    ).fetchall()
    resumen_por_analista: List[dict] = []
    for (analista,) in analistas:
        if not analista:
            continue
        prestamos = db.execute(
            select(Prestamo.id)
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.analista == analista,
                Prestamo.estado == "APROBADO",
            )
        ).fetchall()
        ids = [x[0] for x in prestamos]
        total_prestamos = len(ids)
        total_clientes = db.scalar(select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo).where(Prestamo.id.in_(ids))) or 0
        cartera_total = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.is_(None), Cuota.prestamo_id.in_(ids)))) or 0
        morosidad_total = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < fc, Cuota.prestamo_id.in_(ids)))) or 0
        total_cobrado = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.isnot(None), Cuota.prestamo_id.in_(ids)))) or 0
        porcentaje_cobrado = (total_cobrado / (total_cobrado + cartera_total) * 100) if (total_cobrado + cartera_total) else 0
        porcentaje_morosidad = (morosidad_total / cartera_total * 100) if cartera_total else 0
        resumen_por_analista.append({
            "analista": analista,
            "total_prestamos": total_prestamos,
            "total_clientes": total_clientes,
            "cartera_total": cartera_total,
            "morosidad_total": morosidad_total,
            "total_cobrado": total_cobrado,
            "porcentaje_cobrado": round(porcentaje_cobrado, 2),
            "porcentaje_morosidad": round(porcentaje_morosidad, 2),
        })
    return {
        "fecha_corte": fc.isoformat(),
        "resumen_por_analista": resumen_por_analista,
        "desempeno_mensual": [],
        "clientes_por_analista": [],
    }
