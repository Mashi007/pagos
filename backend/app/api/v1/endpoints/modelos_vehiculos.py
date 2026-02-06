"""
Endpoints de modelos de vehículos. Lectura y escritura desde tabla modelos_vehiculos (precio para Valor Activo).
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.modelo_vehiculo import ModeloVehiculo

router = APIRouter(dependencies=[Depends(get_current_user)])


class ModeloVehiculoCreate(BaseModel):
    modelo: str
    activo: bool = True
    precio: Optional[float] = None


class ModeloVehiculoUpdate(BaseModel):
    modelo: Optional[str] = None
    activo: Optional[bool] = None
    precio: Optional[float] = None


def _row_to_item(row: ModeloVehiculo) -> dict:
    """Convierte fila ModeloVehiculo a dict con precio para el frontend."""
    return {
        "id": row.id,
        "modelo": row.modelo,
        "activo": bool(row.activo),
        "precio": float(row.precio) if row.precio is not None else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _modelos_from_table(
    db: Session,
    skip: int = 0,
    limit: Optional[int] = None,
    activo: Optional[bool] = None,
    search: Optional[str] = None,
) -> tuple[list[dict], int]:
    """Lista desde tabla modelos_vehiculos con precio."""
    q = select(ModeloVehiculo)
    if activo is not None:
        q = q.where(ModeloVehiculo.activo == activo)
    if search and search.strip():
        q = q.where(ModeloVehiculo.modelo.ilike(f"%{search.strip()}%"))
    count_q = select(func.count()).select_from(q.subquery())
    total = db.scalar(count_q) or 0
    q = q.order_by(ModeloVehiculo.modelo).offset(skip)
    if limit is not None:
        q = q.limit(limit)
    rows = db.execute(q).scalars().all()
    return [_row_to_item(r) for r in rows], total


@router.get("", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
def listar_modelos(
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(1000, ge=1, le=5000),
    activo: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Lista modelos de vehículos desde tabla modelos_vehiculos (con precio)."""
    items, total = _modelos_from_table(db, skip=skip, limit=limit, activo=activo, search=search)
    page_size = limit or 1000
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    page = (skip // page_size) + 1 if page_size else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/activos", response_model=list)
def listar_modelos_activos(db: Session = Depends(get_db)):
    """Lista modelos activos con precio para formulario Nuevo Préstamo (Valor Activo)."""
    items, _ = _modelos_from_table(db, skip=0, limit=5000, activo=True)
    return items


@router.get("/{modelo_id}", response_model=dict)
def obtener_modelo(modelo_id: int, db: Session = Depends(get_db)):
    """Obtiene un modelo por ID."""
    row = db.get(ModeloVehiculo, modelo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    return _row_to_item(row)


@router.post("", response_model=dict, status_code=201)
def crear_modelo(
    payload: ModeloVehiculoCreate = Body(...),
    db: Session = Depends(get_db),
):
    """Crea un modelo de vehículo (modelo, activo, precio)."""
    modelo_norm = (payload.modelo or "").strip()
    if not modelo_norm:
        raise HTTPException(status_code=400, detail="El campo modelo es requerido")
    existing = db.execute(
        select(ModeloVehiculo).where(ModeloVehiculo.modelo == modelo_norm)
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un modelo con ese nombre")
    precio_val = None
    if payload.precio is not None:
        try:
            precio_val = Decimal(str(payload.precio))
        except Exception:
            precio_val = None
    row = ModeloVehiculo(
        modelo=modelo_norm,
        activo=payload.activo,
        precio=precio_val,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_item(row)


@router.put("/{modelo_id}", response_model=dict)
def actualizar_modelo(
    modelo_id: int,
    payload: ModeloVehiculoUpdate = Body(...),
    db: Session = Depends(get_db),
):
    """Actualiza un modelo (modelo, activo, precio)."""
    row = db.get(ModeloVehiculo, modelo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    if payload.modelo is not None:
        modelo_norm = (payload.modelo or "").strip()
        if not modelo_norm:
            raise HTTPException(status_code=400, detail="El campo modelo no puede quedar vacío")
        other = db.execute(
            select(ModeloVehiculo).where(
                ModeloVehiculo.modelo == modelo_norm,
                ModeloVehiculo.id != modelo_id,
            )
        ).scalars().first()
        if other:
            raise HTTPException(status_code=409, detail="Ya existe otro modelo con ese nombre")
        row.modelo = modelo_norm
    if payload.activo is not None:
        row.activo = payload.activo
    # Actualizar precio si fue enviado (incluye permitir null para limpiar)
    if "precio" in (payload.model_dump(exclude_unset=True) or {}):
        row.precio = Decimal(str(payload.precio)) if payload.precio is not None else None
    db.commit()
    db.refresh(row)
    return _row_to_item(row)


@router.delete("/{modelo_id}", status_code=204)
def eliminar_modelo(modelo_id: int, db: Session = Depends(get_db)):
    """Elimina un modelo de vehículo."""
    row = db.get(ModeloVehiculo, modelo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    db.delete(row)
    db.commit()
    return None


@router.post("/importar")
def importar_excel(db: Session = Depends(get_db)):
    """Importación desde Excel no implementada."""
    raise HTTPException(
        status_code=501,
        detail="Importación de modelos desde Excel no implementada",
    )
