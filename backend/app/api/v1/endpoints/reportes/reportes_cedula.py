"""
Reportes por cédula.
"""
import io
from datetime import date
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo

from app.api.v1.endpoints.reportes_utils import _safe_float

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/por-cedula")
def get_reportes_por_cedula(db: Session = Depends(get_db)):
    """
    Reporte por cédula: id préstamo, cédula, nombre, total financiamiento, total abono,
    cuotas totales, cuotas pagadas, cuotas atrasadas, monto cuotas atrasadas.
    """
    prestamos = (
        db.execute(
            select(Prestamo)
            .where(Prestamo.estado == "APROBADO")
            .order_by(Prestamo.id)
        )
    ).scalars().all()

    ids = [p.id for p in prestamos]
    abono_map: dict = {}
    pagadas_map: dict = {}
    atrasadas_map: dict = {}
    monto_atrasadas_map: dict = {}

    if ids:
        rows_abono = db.execute(
            select(Pago.prestamo_id, func.coalesce(func.sum(Pago.monto_pagado), 0))
            .where(Pago.prestamo_id.in_(ids))
            .group_by(Pago.prestamo_id)
        ).fetchall()
        abono_map = {r[0]: _safe_float(r[1]) for r in rows_abono}

        rows_pagadas = db.execute(
            select(Cuota.prestamo_id, func.count())
            .where(Cuota.prestamo_id.in_(ids), Cuota.estado == "PAGADO")
            .group_by(Cuota.prestamo_id)
        ).fetchall()
        pagadas_map = {r[0]: int(r[1]) for r in rows_pagadas}

        rows_atrasadas = db.execute(
            select(Cuota.prestamo_id, func.count())
            .where(Cuota.prestamo_id.in_(ids), Cuota.estado != "PAGADO")
            .group_by(Cuota.prestamo_id)
        ).fetchall()
        atrasadas_map = {r[0]: int(r[1]) for r in rows_atrasadas}

        rows_monto_atrasadas = db.execute(
            select(Cuota.prestamo_id, func.coalesce(func.sum(Cuota.monto), 0))
            .where(Cuota.prestamo_id.in_(ids), Cuota.estado != "PAGADO")
            .group_by(Cuota.prestamo_id)
        ).fetchall()
        monto_atrasadas_map = {r[0]: _safe_float(r[1]) for r in rows_monto_atrasadas}

    items: List[dict] = []
    for p in prestamos:
        cedula = p.cedula or ""
        nombre = p.nombres or ""
        if not cedula or not nombre:
            row_cli = db.execute(select(Cliente.cedula, Cliente.nombres).where(Cliente.id == p.cliente_id)).first()
            if row_cli:
                cedula = cedula or (row_cli.cedula or "")
                nombre = nombre or (row_cli.nombres or "")
        items.append({
            "id_prestamo": p.id,
            "cedula": cedula,
            "nombre": nombre,
            "total_financiamiento": round(_safe_float(p.total_financiamiento), 2),
            "total_abono": round(abono_map.get(p.id, 0), 2),
            "cuotas_totales": p.numero_cuotas or 0,
            "cuotas_pagadas": pagadas_map.get(p.id, 0),
            "cuotas_atrasadas": atrasadas_map.get(p.id, 0),
            "monto_cuotas_atrasadas": round(monto_atrasadas_map.get(p.id, 0), 2),
        })
    return {"items": items}


def _generar_excel_por_cedula(items: List[dict]) -> bytes:
    """Genera Excel reporte por cédula."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    hoy = date.today()
    meses_es = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    mes_es = meses_es.get(hoy.month, "")
    ano = hoy.year
    titulo_pestana = f"Por cédula - {mes_es} {ano}"
    ws.title = titulo_pestana
    ws.append(["Reporte por cédula"])
    ws.append([])
    total_financiamiento = sum(r.get("total_financiamiento", 0) for r in items)
    total_abono = sum(r.get("total_abono", 0) for r in items)
    total_atrasos = sum(r.get("monto_cuotas_atrasadas", 0) for r in items)
    ws.append([f"Total financiamiento: ${total_financiamiento:.2f} | Total abono: ${total_abono:.2f} | Total atrasos: ${total_atrasos:.2f}"])
    ws.append([])
    ws.append([
        "ID Préstamo", "Cédula", "Nombre", "Total financiamiento ($)", "Total abono ($)",
        "Cuotas totales", "Cuotas pagadas", "Cuotas atrasadas", "Cuotas atrasadas ($)",
    ])
    for r in items:
        ws.append([
            str(r.get("id_prestamo", "")), r.get("cedula", ""), r.get("nombre", ""),
            r.get("total_financiamiento", 0), r.get("total_abono", 0),
            r.get("cuotas_totales", 0), r.get("cuotas_pagadas", 0),
            r.get("cuotas_atrasadas", 0), r.get("monto_cuotas_atrasadas", 0),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/exportar/cedula")
def exportar_cedula(db: Session = Depends(get_db)):
    """Exporta reporte por cédula en Excel."""
    data = get_reportes_por_cedula(db=db)
    items = data.get("items", [])
    content = _generar_excel_por_cedula(items)
    hoy_str = date.today().isoformat()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reporte_por_cedula_{hoy_str}.xlsx"},
    )
