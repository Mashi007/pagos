"""
Endpoints de préstamos. Datos reales desde BD (tabla prestamos).
Todos los endpoints usan Depends(get_db). No hay stubs ni datos demo.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.schemas.prestamo import PrestamoCreate, PrestamoResponse, PrestamoUpdate, PrestamoListResponse

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
def listar_prestamos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cliente_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Listado paginado de préstamos desde BD con nombres y cédula del cliente (join)."""
    count_q = select(func.count()).select_from(Prestamo)
    q = select(Prestamo, Cliente.nombres, Cliente.cedula).select_from(Prestamo).join(
        Cliente, Prestamo.cliente_id == Cliente.id
    )
    if cliente_id is not None:
        q = q.where(Prestamo.cliente_id == cliente_id)
        count_q = count_q.where(Prestamo.cliente_id == cliente_id)
    if estado and estado.strip():
        est = estado.strip().upper()
        q = q.where(Prestamo.estado == est)
        count_q = count_q.where(Prestamo.estado == est)
    if analista and analista.strip():
        q = q.where(Prestamo.analista == analista.strip())
        count_q = count_q.where(Prestamo.analista == analista.strip())
    if concesionario and concesionario.strip():
        q = q.where(Prestamo.concesionario == concesionario.strip())
        count_q = count_q.where(Prestamo.concesionario == concesionario.strip())
    total = db.scalar(count_q) or 0
    q = q.order_by(Prestamo.id.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = db.execute(q).all()
    prestamo_ids = [row[0].id for row in rows]
    # Conteo de cuotas por préstamo (para mostrar en columna Cuotas)
    cuotas_por_prestamo = {}
    if prestamo_ids:
        cuenta = select(Cuota.prestamo_id, func.count()).select_from(Cuota).where(
            Cuota.prestamo_id.in_(prestamo_ids)
        ).group_by(Cuota.prestamo_id)
        for pid, cnt in db.execute(cuenta).all():
            cuotas_por_prestamo[pid] = cnt
    items = []
    for row in rows:
        p, nombres_cliente, cedula_cliente = row[0], row[1], row[2]
        # Cuotas: preferir conteo desde tabla cuotas; si no hay, usar columna numero_cuotas
        numero_cuotas = cuotas_por_prestamo.get(p.id) if cuotas_por_prestamo.get(p.id) is not None else p.numero_cuotas
        item = PrestamoListResponse(
            id=p.id,
            cliente_id=p.cliente_id,
            total_financiamiento=p.total_financiamiento,
            estado=p.estado,
            concesionario=p.concesionario,
            modelo=p.modelo,
            analista=p.analista,
            fecha_creacion=p.fecha_creacion,
            fecha_actualizacion=p.fecha_actualizacion,
            fecha_registro=p.fecha_registro,
            fecha_aprobacion=p.fecha_aprobacion,
            nombres=nombres_cliente or p.nombres,
            cedula=cedula_cliente or p.cedula,
            numero_cuotas=numero_cuotas,
            modalidad_pago=p.modalidad_pago,
        )
        items.append(item)
    total_pages = (total + per_page - 1) // per_page if total else 0
    return {
        "prestamos": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.get("/stats", response_model=dict)
def get_prestamos_stats(db: Session = Depends(get_db)):
    """Estadísticas de préstamos desde BD (total, por estado)."""
    total = db.scalar(select(func.count()).select_from(Prestamo)) or 0
    rows = db.execute(
        select(Prestamo.estado, func.count()).select_from(Prestamo).group_by(Prestamo.estado)
    ).all()
    por_estado = {r[0]: r[1] for r in rows}
    return {"total": total, "por_estado": por_estado}


@router.get("/{prestamo_id}", response_model=PrestamoResponse)
def get_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    """Obtiene un préstamo por ID desde BD."""
    row = db.get(Prestamo, prestamo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    return PrestamoResponse.model_validate(row)


@router.post("", response_model=PrestamoResponse, status_code=201)
def create_prestamo(payload: PrestamoCreate, db: Session = Depends(get_db)):
    """Crea un préstamo en BD. Valida que cliente_id exista. cedula/nombres se toman del Cliente."""
    cliente = db.get(Cliente, payload.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    from datetime import date
    hoy = date.today()
    row = Prestamo(
        cliente_id=payload.cliente_id,
        cedula=cliente.cedula or "",
        nombres=cliente.nombres or "",
        total_financiamiento=payload.total_financiamiento,
        fecha_requerimiento=payload.fecha_requerimiento or hoy,
        modalidad_pago=payload.modalidad_pago or "MENSUAL",
        numero_cuotas=payload.numero_cuotas or 12,
        cuota_periodo=payload.cuota_periodo or 0,
        producto=payload.producto or "Financiamiento",
        estado=payload.estado or "DRAFT",
        concesionario=payload.concesionario,
        modelo_vehiculo=payload.modelo,
        analista=payload.analista or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PrestamoResponse.model_validate(row)


@router.put("/{prestamo_id}", response_model=PrestamoResponse)
def update_prestamo(prestamo_id: int, payload: PrestamoUpdate, db: Session = Depends(get_db)):
    """Actualiza un préstamo en BD."""
    row = db.get(Prestamo, prestamo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    if payload.cliente_id is not None:
        cliente = db.get(Cliente, payload.cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        row.cliente_id = payload.cliente_id
    if payload.total_financiamiento is not None:
        row.total_financiamiento = payload.total_financiamiento
    if payload.estado is not None:
        row.estado = payload.estado
    if payload.concesionario is not None:
        row.concesionario = payload.concesionario
    if payload.modelo is not None:
        row.modelo_vehiculo = payload.modelo
    if payload.analista is not None:
        row.analista = payload.analista
    if payload.modalidad_pago is not None:
        row.modalidad_pago = payload.modalidad_pago
    if payload.numero_cuotas is not None:
        row.numero_cuotas = payload.numero_cuotas
    db.commit()
    db.refresh(row)
    return PrestamoResponse.model_validate(row)


@router.delete("/{prestamo_id}", status_code=204)
def delete_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    """Elimina un préstamo en BD."""
    row = db.get(Prestamo, prestamo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    db.delete(row)
    db.commit()
    return None
