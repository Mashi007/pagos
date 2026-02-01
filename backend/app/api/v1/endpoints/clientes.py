"""
Endpoints de clientes: CONECTADOS A LA TABLA REAL `clientes` (public.clientes).
- Conexión: engine/sesión desde app.core.database (DATABASE_URL en .env).
- Modelo: app.models.cliente.Cliente con __tablename__ = "clientes".
- Todos los datos son REALES: listado, stats, get, create, update, delete y cambio de estado
  usan Depends(get_db) y consultas contra la tabla clientes. No hay stubs ni datos demo.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteResponse, ClienteCreate, ClienteUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", summary="Listado paginado", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
def get_clientes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Listado paginado de clientes desde la BD.
    Filtros: search (cedula, nombres, email, telefono), estado (ACTIVO, INACTIVO, MORA, FINALIZADO).
    """
    try:
        q = select(Cliente)
        count_q = select(func.count()).select_from(Cliente)

        if search and search.strip():
            t = f"%{search.strip()}%"
            filtro = or_(
                Cliente.cedula.ilike(t),
                Cliente.nombres.ilike(t),
                Cliente.email.ilike(t),
                Cliente.telefono.ilike(t),
            )
            q = q.where(filtro)
            count_q = count_q.where(filtro)
        if estado and estado.strip():
            est = estado.strip().upper()
            q = q.where(Cliente.estado == est)
            count_q = count_q.where(Cliente.estado == est)

        total = db.scalar(count_q) or 0
        q = q.order_by(Cliente.id.desc()).offset((page - 1) * per_page).limit(per_page)
        result = db.execute(q)
        rows = result.scalars().all()

        total_pages = (total + per_page - 1) // per_page if total else 0

        return {
            "clientes": [ClienteResponse.model_validate(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.exception("Error en listado de clientes: %s", e)
        raise HTTPException(status_code=500, detail="Error al cargar el listado de clientes") from e


@router.get("/stats")
def get_clientes_stats(db: Session = Depends(get_db)):
    """
    Estadísticas de clientes por estado: total, activos, inactivos, finalizados.
    """
    total = db.scalar(select(func.count()).select_from(Cliente)) or 0
    activos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "ACTIVO")) or 0
    inactivos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "INACTIVO")) or 0
    finalizados = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "FINALIZADO")) or 0
    return {
        "total": total,
        "activos": activos,
        "inactivos": inactivos,
        "finalizados": finalizados,
    }


class EstadoPayload(BaseModel):
    estado: str


@router.patch("/{cliente_id}/estado", response_model=ClienteResponse)
def cambiar_estado_cliente(
    cliente_id: int,
    payload: EstadoPayload,
    db: Session = Depends(get_db),
):
    """Cambiar estado del cliente (PATCH /clientes/{id}/estado)."""
    from fastapi import HTTPException
    row = db.get(Cliente, cliente_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    estado = payload.estado
    if estado not in ("ACTIVO", "INACTIVO", "MORA", "FINALIZADO"):
        raise HTTPException(status_code=400, detail="estado debe ser ACTIVO, INACTIVO, MORA o FINALIZADO")
    row.estado = estado
    db.commit()
    db.refresh(row)
    return ClienteResponse.model_validate(row)


@router.get("/{cliente_id}", response_model=ClienteResponse)
def get_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtener un cliente por ID."""
    row = db.get(Cliente, cliente_id)
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return ClienteResponse.model_validate(row)


@router.post("", response_model=ClienteResponse, status_code=201)
def create_cliente(payload: ClienteCreate, db: Session = Depends(get_db)):
    """Crear cliente en la BD."""
    row = Cliente(
        cedula=payload.cedula,
        nombres=payload.nombres,
        telefono=payload.telefono,
        email=payload.email,
        direccion=payload.direccion,
        fecha_nacimiento=payload.fecha_nacimiento,
        ocupacion=payload.ocupacion,
        estado=payload.estado,
        usuario_registro=payload.usuario_registro,
        notas=payload.notas,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ClienteResponse.model_validate(row)


@router.put("/{cliente_id}", response_model=ClienteResponse)
def update_cliente(cliente_id: int, payload: ClienteUpdate, db: Session = Depends(get_db)):
    """Actualizar cliente."""
    row = db.get(Cliente, cliente_id)
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return ClienteResponse.model_validate(row)


@router.delete("/{cliente_id}", status_code=204)
def delete_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Eliminar cliente."""
    row = db.get(Cliente, cliente_id)
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    db.delete(row)
    db.commit()
    return None
