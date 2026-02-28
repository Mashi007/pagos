"""
Reporte Conciliación: Excel con datos de clientes, préstamos, pagos, cuotas y tabla temporal.
- Carga Excel (columnas por cédula) → guardar en conciliacion_temporal.
- Descarga Excel (columnas A–L) → al descargar se vacía conciliacion_temporal.
"""
import io
import re
from datetime import date
from decimal import Decimal
from typing import Any, List

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select, delete
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.conciliacion_temporal import ConciliacionTemporal
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo

from app.api.v1.endpoints.reportes_utils import _safe_float

router = APIRouter(dependencies=[Depends(get_current_user)])

# Validación cédula: al menos 5 dígitos/letras (ajustar según reglas de negocio)
CEDULA_PATTERN = re.compile(r"^[A-Za-z0-9\-]{5,20}$")


def _validar_cedula(cedula: Any) -> bool:
    if cedula is None:
        return False
    s = str(cedula).strip()
    return bool(s and CEDULA_PATTERN.match(s))


def _validar_numero(val: Any) -> bool:
    if val is None:
        return False
    try:
        f = float(val)
        return f >= 0
    except (TypeError, ValueError):
        return False


def _parse_numero(val: Any) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")


@router.post("/conciliacion/cargar")
def cargar_conciliacion_temporal(
    body: List[dict] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Recibe lista de filas: cedula, total_financiamiento, total_abonos, columna_e (opcional), columna_f (opcional).
    Valida cédula y cantidades; si todo es válido borra datos previos e inserta los nuevos.
    """
    if not body or not isinstance(body, list):
        raise HTTPException(status_code=400, detail="Se requiere una lista de filas")
    errores: List[str] = []
    filas_ok: List[dict] = []
    for i, row in enumerate(body):
        if not isinstance(row, dict):
            errores.append(f"Fila {i + 1}: debe ser un objeto con cedula, total_financiamiento, total_abonos")
            continue
        cedula = row.get("cedula")
        tf = row.get("total_financiamiento")
        ta = row.get("total_abonos")
        if not _validar_cedula(cedula):
            errores.append(f"Fila {i + 1}: cédula inválida")
            continue
        if not _validar_numero(tf):
            errores.append(f"Fila {i + 1}: total financiamiento debe ser un número >= 0")
            continue
        if not _validar_numero(ta):
            errores.append(f"Fila {i + 1}: total abonos debe ser un número >= 0")
            continue
        filas_ok.append({
            "cedula": str(cedula).strip(),
            "total_financiamiento": _parse_numero(tf),
            "total_abonos": _parse_numero(ta),
            "columna_e": str(row.get("columna_e") or "").strip() or None,
            "columna_f": str(row.get("columna_f") or "").strip() or None,
        })
    if errores:
        raise HTTPException(status_code=422, detail={"errores": errores, "mensaje": "Corrija los errores antes de guardar"})
    db.execute(delete(ConciliacionTemporal))
    for f in filas_ok:
        db.add(ConciliacionTemporal(
            cedula=f["cedula"],
            total_financiamiento=f["total_financiamiento"],
            total_abonos=f["total_abonos"],
            columna_e=f.get("columna_e"),
            columna_f=f.get("columna_f"),
        ))
    db.commit()
    return {"ok": True, "filas_guardadas": len(filas_ok)}


def _generar_excel_conciliacion(db: Session) -> bytes:
    """Genera Excel reporte Conciliación (columnas A–L) y deja lista la eliminación de temporales."""
    import openpyxl

    prestamos = (
        db.execute(
            select(Prestamo)
            .where(Prestamo.estado == "APROBADO")
            .order_by(Prestamo.id)
        )
    ).scalars().all()

    # Mapa cedula -> conciliacion_temporal (una fila por cédula; si hay varias tomamos la primera)
    concilia_rows = db.execute(select(ConciliacionTemporal)).fetchall()
    concilia_por_cedula: dict = {}
    for r in concilia_rows:
        c = r[0] if hasattr(r, "__getitem__") else r
        if c.cedula not in concilia_por_cedula:
            concilia_por_cedula[c.cedula] = c

    ids = [p.id for p in prestamos]
    total_pagos_map: dict = {}
    total_cuotas_num_map: dict = {}
    cuotas_pagadas_num_map: dict = {}
    cuotas_pagadas_monto_map: dict = {}
    cuotas_pendientes_num_map: dict = {}
    cuotas_pendientes_monto_map: dict = {}

    if ids:
        total_pagos_map = dict(
            db.execute(
                select(Pago.prestamo_id, func.coalesce(func.sum(Pago.monto_pagado), 0))
                .where(Pago.prestamo_id.isnot(None), Pago.prestamo_id.in_(ids))
                .group_by(Pago.prestamo_id)
            ).fetchall()
        )
        # Total cuotas por préstamo: count y sum(monto)
        rows_tot = db.execute(
            select(Cuota.prestamo_id, func.count())
            .where(Cuota.prestamo_id.in_(ids))
            .group_by(Cuota.prestamo_id)
        ).fetchall()
        for r in rows_tot:
            total_cuotas_num_map[r[0]] = int(r[1])
        # Cuotas pagadas (estado PAGADO)
        rows_pag = db.execute(
            select(Cuota.prestamo_id, func.count(), func.coalesce(func.sum(Cuota.monto), 0))
            .where(Cuota.prestamo_id.in_(ids), Cuota.estado == "PAGADO")
            .group_by(Cuota.prestamo_id)
        ).fetchall()
        for r in rows_pag:
            cuotas_pagadas_num_map[r[0]] = int(r[1])
            cuotas_pagadas_monto_map[r[0]] = _safe_float(r[2])
        # Cuotas pendientes (estado != PAGADO): count y sum(monto)
        rows_pend = db.execute(
            select(Cuota.prestamo_id, func.count(), func.coalesce(func.sum(Cuota.monto), 0))
            .where(Cuota.prestamo_id.in_(ids), Cuota.estado != "PAGADO")
            .group_by(Cuota.prestamo_id)
        ).fetchall()
        for r in rows_pend:
            cuotas_pendientes_num_map[r[0]] = int(r[1])
            cuotas_pendientes_monto_map[r[0]] = _safe_float(r[2])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Conciliacion"
    ws.append([
        "Nombre", "Cedula", "Numero de credito", "Total financiamiento",
        "Columna E", "Columna F",
        "Total pagos realizados", "Total cuotas",
        "Cuotas pagadas (num)", "Cuotas pagadas ($)",
        "Cuotas pendientes (num)", "Cuotas pendientes ($)",
    ])
    for p in prestamos:
        cedula = (p.cedula or "").strip()
        nombres = (p.nombres or "").strip()
        cliente = db.execute(select(Cliente).where(Cliente.id == p.cliente_id)).scalar().first() if p.cliente_id else None
        if cliente:
            nombres = (cliente.nombres or nombres or "").strip()
            cedula = (cliente.cedula or cedula or "").strip()
        else:
            if not nombres and not cedula:
                nombres = "no existe"
                cedula = "no existe"
        concilia = concilia_por_cedula.get(cedula) if cedula and cedula != "no existe" else None
        col_e = concilia.columna_e if concilia else ""
        col_f = concilia.columna_f if concilia else ""
        total_pagos = _safe_float(total_pagos_map.get(p.id, 0))
        tot_cuotas = total_cuotas_num_map.get(p.id, p.numero_cuotas or 0)
        pag_num = cuotas_pagadas_num_map.get(p.id, 0)
        pag_monto = cuotas_pagadas_monto_map.get(p.id, 0)
        pend_num = cuotas_pendientes_num_map.get(p.id, 0)
        pend_monto = cuotas_pendientes_monto_map.get(p.id, 0)
        ws.append([
            nombres, cedula, p.id, _safe_float(p.total_financiamiento),
            col_e or "", col_f or "",
            round(total_pagos, 2), tot_cuotas,
            pag_num, round(pag_monto, 2),
            pend_num, round(pend_monto, 2),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/exportar/conciliacion")
def exportar_conciliacion(db: Session = Depends(get_db)):
    """
    Genera Excel de conciliación (columnas A–L) y elimina los registros de conciliacion_temporal.
    """
    content = _generar_excel_conciliacion(db)
    db.execute(delete(ConciliacionTemporal))
    db.commit()
    hoy_str = date.today().isoformat()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reporte_conciliacion_{hoy_str}.xlsx"},
    )
