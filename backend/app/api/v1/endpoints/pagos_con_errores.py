"""
Endpoints para pagos_con_errores: pagos con errores de validaciÃ³n desde Carga Masiva.
Revisar Pagos y front apuntan a esta tabla. No se mezclan con pagos que cumplen validadores.
"""
import logging
from datetime import date, datetime, time as dt_time
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.pago_con_error import PagoConError

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


class PagoConErrorCreate(BaseModel):
    cedula_cliente: str
    prestamo_id: Optional[int] = None
    fecha_pago: str
    monto_pagado: float
    numero_documento: Optional[str] = None
    institucion_bancaria: Optional[str] = None
    notas: Optional[str] = None
    conciliado: Optional[bool] = False
    errores_descripcion: Optional[list[dict]] = None
    observaciones: Optional[str] = None  # Nombres de campos con problema, separados por coma
    fila_origen: Optional[int] = None


class PagoConErrorUpdate(BaseModel):
    cedula_cliente: Optional[str] = None
    prestamo_id: Optional[int] = None
    fecha_pago: Optional[str] = None
    monto_pagado: Optional[float] = None
    numero_documento: Optional[str] = None
    institucion_bancaria: Optional[str] = None
    notas: Optional[str] = None
    conciliado: Optional[bool] = None
    errores_descripcion: Optional[list[dict]] = None
    observaciones: Optional[str] = None


def _pago_con_error_to_response(row: PagoConError) -> dict:
    fp = row.fecha_pago
    fecha_pago_str = fp.date().isoformat() if hasattr(fp, "date") and fp else (fp.isoformat() if fp else "")
    return {
        "id": row.id,
        "cedula_cliente": row.cedula_cliente or "",
        "prestamo_id": row.prestamo_id,
        "fecha_pago": fecha_pago_str,
        "monto_pagado": float(row.monto_pagado) if row.monto_pagado is not None else 0,
        "numero_documento": row.numero_documento or "",
        "institucion_bancaria": row.institucion_bancaria,
        "estado": row.estado or "PENDIENTE",
        "fecha_registro": row.fecha_registro.isoformat() if row.fecha_registro else None,
        "fecha_conciliacion": row.fecha_conciliacion.isoformat() if row.fecha_conciliacion else None,
        "conciliado": bool(row.conciliado),
        "verificado_concordancia": getattr(row, "verificado_concordancia", None) or None,
        "usuario_registro": row.usuario_registro or "",
        "notas": row.notas,
        "documento_nombre": getattr(row, "documento_nombre", None),
        "documento_tipo": getattr(row, "documento_tipo", None),
        "documento_ruta": getattr(row, "documento_ruta", None),
        "errores_descripcion": row.errores_descripcion,
        "observaciones": getattr(row, "observaciones", None) or "",
        "fila_origen": row.fila_origen,
    }


@router.get("", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
def listar_pagos_con_errores(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cedula: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    conciliado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Listado paginado de pagos con errores (Revisar Pagos). Se vacÃ­a al descargar Excel."""
    try:
        q = select(PagoConError)
        count_q = select(func.count()).select_from(PagoConError)
        if conciliado and conciliado.strip().lower() == "si":
            q = q.where(PagoConError.conciliado == True)
            count_q = count_q.where(PagoConError.conciliado == True)
        elif conciliado and conciliado.strip().lower() == "no":
            q = q.where(or_(PagoConError.conciliado == False, PagoConError.conciliado.is_(None)))
            count_q = count_q.where(or_(PagoConError.conciliado == False, PagoConError.conciliado.is_(None)))
        if cedula and cedula.strip():
            q = q.where(PagoConError.cedula_cliente.ilike(f"%{cedula.strip()}%"))
            count_q = count_q.where(PagoConError.cedula_cliente.ilike(f"%{cedula.strip()}%"))
        if estado and estado.strip():
            q = q.where(PagoConError.estado == estado.strip().upper())
            count_q = count_q.where(PagoConError.estado == estado.strip().upper())
        if fecha_desde:
            try:
                fd = date.fromisoformat(fecha_desde)
                q = q.where(PagoConError.fecha_pago >= datetime.combine(fd, dt_time.min))
                count_q = count_q.where(PagoConError.fecha_pago >= datetime.combine(fd, dt_time.min))
            except ValueError:
                pass
        if fecha_hasta:
            try:
                fh = date.fromisoformat(fecha_hasta)
                q = q.where(PagoConError.fecha_pago <= datetime.combine(fh, dt_time.max))
                count_q = count_q.where(PagoConError.fecha_pago <= datetime.combine(fh, dt_time.max))
            except ValueError:
                pass
        total = db.scalar(count_q) or 0
        q = q.order_by(PagoConError.fecha_registro.desc().nullslast(), PagoConError.id.desc())
        q = q.offset((page - 1) * per_page).limit(per_page)
        rows = db.execute(q).scalars().all()
        items = [_pago_con_error_to_response(r) for r in rows]
        total_pages = (total + per_page - 1) // per_page if total else 0
        return {
            "pagos": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.exception("Error en GET /pagos/con-errores: %s", e)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=dict, status_code=201)
@router.post("/", include_in_schema=False, response_model=dict, status_code=201)
def crear_pago_con_error(payload: PagoConErrorCreate, db: Session = Depends(get_db)):
    """Crea un pago con errores desde Carga Masiva (Revisar Pagos)."""
    try:
        fecha_ts = datetime.strptime(payload.fecha_pago, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        raise HTTPException(status_code=400, detail="fecha_pago debe ser YYYY-MM-DD")
    ref = (payload.numero_documento or "").strip() or "N/A"
    row = PagoConError(
        cedula_cliente=payload.cedula_cliente.strip(),
        prestamo_id=payload.prestamo_id,
        fecha_pago=fecha_ts,
        monto_pagado=payload.monto_pagado,
        numero_documento=(payload.numero_documento or "").strip() or None,
        institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,
        estado="PENDIENTE",
        conciliado=payload.conciliado if payload.conciliado is not None else False,
        notas=payload.notas,
        referencia_pago=ref,
        errores_descripcion=payload.errores_descripcion,
        observaciones=(payload.observaciones or "").strip() or None,
        fila_origen=payload.fila_origen,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _pago_con_error_to_response(row)


class EliminarPorDescargaBody(BaseModel):
    ids: list[int]


@router.post("/eliminar-por-descarga", response_model=dict)
def eliminar_por_descarga(payload: EliminarPorDescargaBody = Body(...), db: Session = Depends(get_db)):
    """Elimina de pagos_con_errores los registros descargados. La lista se vacÃ­a y se rellena al enviar desde Carga Masiva."""
    if not payload.ids:
        return {"eliminados": 0, "mensaje": "No hay IDs"}
    eliminados = 0
    for pid in payload.ids:
        if not isinstance(pid, int) or pid <= 0:
            continue
        row = db.get(PagoConError, pid)
        if row:
            db.delete(row)
            eliminados += 1
    db.commit()
    return {"eliminados": eliminados, "mensaje": f"{eliminados} eliminados de pagos_con_errores"}


@router.get("/export", response_model=list)
def exportar_pagos_con_errores(
    cedula: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Exporta todos los pagos con errores para Excel (100% de datos). Tras descargar se eliminan de la tabla."""
    q = select(PagoConError).order_by(
        PagoConError.fecha_registro.desc().nullslast(), PagoConError.id.desc()
    )
    if cedula and cedula.strip():
        q = q.where(PagoConError.cedula_cliente.ilike(f"%{cedula.strip()}%"))
    if fecha_desde:
        try:
            fd = date.fromisoformat(fecha_desde)
            q = q.where(PagoConError.fecha_pago >= datetime.combine(fd, dt_time.min))
        except ValueError:
            pass
    if fecha_hasta:
        try:
            fh = date.fromisoformat(fecha_hasta)
            q = q.where(PagoConError.fecha_pago <= datetime.combine(fh, dt_time.max))
        except ValueError:
            pass
    rows = db.execute(q).scalars().all()
    return [_pago_con_error_to_response(r) for r in rows]


@router.post("/mover-a-pagos", response_model=dict)
def mover_a_pagos_normales(
    payload: dict = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Mueve pagos corregidos de pagos_con_errores a pagos (y los elimina de con_errores)."""
    ids = payload.get("ids", [])
    if not ids:
        return {"movidos": 0, "mensaje": "No hay IDs"}
    from app.models.pago import Pago

    movidos = 0
    for pid in ids:
        if not isinstance(pid, int) or pid <= 0:
            continue
        row = db.get(PagoConError, pid)
        if not row:
            continue
        pago = Pago(
            cedula_cliente=row.cedula_cliente,
            prestamo_id=row.prestamo_id,
            fecha_pago=row.fecha_pago,
            monto_pagado=row.monto_pagado,
            numero_documento=row.numero_documento or "",
            institucion_bancaria=row.institucion_bancaria,
            estado=row.estado or "PENDIENTE",
            conciliado=row.conciliado,
            notas=row.notas,
            referencia_pago=row.referencia_pago or row.numero_documento or "N/A",
        )
        db.add(pago)
        db.delete(row)
        movidos += 1
    db.commit()
    return {"movidos": movidos, "mensaje": f"{movidos} pagos movidos a tabla pagos"}


@router.get("/{pago_id}", response_model=dict)
def obtener_pago_con_error(pago_id: int, db: Session = Depends(get_db)):
    row = db.get(PagoConError, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago con error no encontrado")
    return _pago_con_error_to_response(row)


@router.put("/{pago_id}", response_model=dict)
def actualizar_pago_con_error(pago_id: int, payload: PagoConErrorUpdate, db: Session = Depends(get_db)):
    row = db.get(PagoConError, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago con error no encontrado")
    if payload.cedula_cliente is not None:
        row.cedula_cliente = payload.cedula_cliente.strip()
    if payload.prestamo_id is not None:
        row.prestamo_id = payload.prestamo_id
    if payload.fecha_pago is not None:
        try:
            row.fecha_pago = datetime.strptime(payload.fecha_pago, "%Y-%m-%d").replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="fecha_pago debe ser YYYY-MM-DD")
    if payload.monto_pagado is not None:
        row.monto_pagado = payload.monto_pagado
    if payload.numero_documento is not None:
        row.numero_documento = payload.numero_documento.strip() or None
    if payload.institucion_bancaria is not None:
        row.institucion_bancaria = payload.institucion_bancaria.strip() or None
    if payload.notas is not None:
        row.notas = payload.notas
    if payload.conciliado is not None:
        row.conciliado = payload.conciliado
    if payload.errores_descripcion is not None:
        row.errores_descripcion = payload.errores_descripcion
    if payload.observaciones is not None:
        row.observaciones = payload.observaciones.strip() or None
    db.commit()
    db.refresh(row)
    return _pago_con_error_to_response(row)


@router.delete("/{pago_id}", status_code=204)
def eliminar_pago_con_error(pago_id: int, db: Session = Depends(get_db)):
    row = db.get(PagoConError, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago con error no encontrado")
    db.delete(row)
    db.commit()
    return None
