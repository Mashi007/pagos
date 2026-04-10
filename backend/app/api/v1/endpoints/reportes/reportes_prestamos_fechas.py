"""
Excel FECHAS: todos los prestamos (cualquier estado), columnas de fechas clave.
"""
from __future__ import annotations

import io
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo

from app.api.v1.endpoints.reportes_utils import _safe_float

router = APIRouter(dependencies=[Depends(get_current_user)])


def _fmt_dt(v: Optional[datetime]) -> str:
    if v is None:
        return ""
    if hasattr(v, "isoformat"):
        return v.isoformat(sep=" ", timespec="seconds")
    return str(v)


def _fmt_date(v: Optional[date]) -> str:
    if v is None:
        return ""
    return v.isoformat()


def _generar_excel_fechas_prestamos(rows: list[dict]) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "FECHAS"
    ws.append(
        [
            "ID prestamo",
            "C\u00e9dula",
            "Estado",
            "Fecha de registro",
            "Fecha de requerimiento",
            "Fecha de aprobaci\u00f3n",
            "Fecha de c\u00e1lculo",
            "Total financiamiento",
        ]
    )
    for r in rows:
        ws.append(
            [
                r["id_prestamo"],
                r["cedula"],
                r["estado"],
                r["fecha_registro"],
                r["fecha_requerimiento"],
                r["fecha_aprobacion"],
                r["fecha_calculo"],
                r["total_financiamiento"],
            ]
        )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/exportar/prestamos-fechas")
def exportar_prestamos_fechas_excel(db: Session = Depends(get_db)):
    """
    Descarga Excel (hoja FECHAS) con todos los prestamos en cualquier estado:
    ID, cedula, estado, fecha registro, fecha requerimiento, fecha aprobacion,
    fecha calculo (base), total financiamiento.
    """
    prestamos = db.execute(select(Prestamo).order_by(Prestamo.id)).scalars().all()
    out: list[dict] = []
    for p in prestamos:
        cedula = (p.cedula or "").strip()
        if not cedula and p.cliente_id:
            row_cli = db.execute(
                select(Cliente.cedula).where(Cliente.id == p.cliente_id)
            ).first()
            if row_cli and row_cli[0]:
                cedula = str(row_cli[0]).strip()
        out.append(
            {
                "id_prestamo": p.id,
                "cedula": cedula,
                "estado": (getattr(p, "estado", None) or "").strip(),
                "fecha_registro": _fmt_dt(getattr(p, "fecha_registro", None)),
                "fecha_requerimiento": _fmt_date(
                    getattr(p, "fecha_requerimiento", None)
                ),
                "fecha_aprobacion": _fmt_dt(getattr(p, "fecha_aprobacion", None)),
                "fecha_calculo": _fmt_date(getattr(p, "fecha_base_calculo", None)),
                "total_financiamiento": round(_safe_float(p.total_financiamiento), 2),
            }
        )
    content = _generar_excel_fechas_prestamos(out)
    hoy_str = date.today().isoformat()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename=FECHAS_solo_sistema_8cols_{hoy_str}.xlsx"
            )
        },
    )
