"""
Endpoints de modelos de vehículos. Lectura desde BD: distinct Prestamo.modelo_vehiculo.
Sin tabla modelo_vehiculo: listado y activos desde préstamos; CRUD devuelve 501.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.prestamo import Prestamo

router = APIRouter(dependencies=[Depends(get_current_user)])


def _modelos_from_db(
    db: Session,
    skip: int = 0,
    limit: Optional[int] = None,
    activo: Optional[bool] = None,
    search: Optional[str] = None,
) -> tuple[list[dict], int]:
    """Obtiene lista de modelos (distinct Prestamo.modelo_vehiculo) con id sintético. activo/search se ignoran (todos activos)."""
    col = Prestamo.modelo_vehiculo
    q = select(col).where(col.isnot(None), col != "").distinct()
    if search and search.strip():
        q = q.where(col.ilike(f"%{search.strip()}%"))
    count_q = select(func.count()).select_from(q.subquery())
    total = db.scalar(count_q) or 0
    q = q.order_by(col).offset(skip)
    if limit is not None:
        q = q.limit(limit)
    rows = db.execute(q).scalars().all()
    now_iso = datetime.now(timezone.utc).isoformat()
    items = [
        {
            "id": i + 1,
            "modelo": name,
            "activo": True,
            "precio": None,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        for i, name in enumerate(rows)
    ]
    return items, total


@router.get("", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
def listar_modelos(
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(1000, ge=1, le=5000),
    activo: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Lista modelos de vehículos desde distinct Prestamo.modelo (solo lectura)."""
    items, total = _modelos_from_db(db, skip=skip, limit=limit, activo=activo, search=search)
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
    """Lista modelos activos (distinct Prestamo.modelo) para formularios."""
    items, _ = _modelos_from_db(db, skip=0, limit=5000)
    return items


@router.get("/{modelo_id}")
def obtener_modelo(modelo_id: int, db: Session = Depends(get_db)):
    """Por ahora no hay tabla modelo_vehiculo; devolver 501."""
    raise HTTPException(status_code=501, detail="CRUD de modelos de vehículos no implementado (solo lectura desde préstamos)")


@router.post("")
def crear_modelo(db: Session = Depends(get_db)):
    """Por ahora no hay tabla modelo_vehiculo; devolver 501."""
    raise HTTPException(status_code=501, detail="CRUD de modelos de vehículos no implementado (solo lectura desde préstamos)")


@router.put("/{modelo_id}")
def actualizar_modelo(modelo_id: int, db: Session = Depends(get_db)):
    """Por ahora no hay tabla modelo_vehiculo; devolver 501."""
    raise HTTPException(status_code=501, detail="CRUD de modelos de vehículos no implementado (solo lectura desde préstamos)")


@router.delete("/{modelo_id}")
def eliminar_modelo(modelo_id: int, db: Session = Depends(get_db)):
    """Por ahora no hay tabla modelo_vehiculo; devolver 501."""
    raise HTTPException(status_code=501, detail="CRUD de modelos de vehículos no implementado (solo lectura desde préstamos)")


@router.post("/importar")
def importar_excel(db: Session = Depends(get_db)):
    """Por ahora no hay tabla modelo_vehiculo; devolver 501."""
    raise HTTPException(status_code=501, detail="Importación de modelos no implementada (solo lectura desde préstamos)")
