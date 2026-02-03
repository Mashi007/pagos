"""
Endpoints de concesionarios. Lectura desde BD: distinct Prestamo.concesionario.
Sin tabla concesionarios: listado y activos desde préstamos; CRUD devuelve 501.
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


def _concesionarios_from_db(
    db: Session,
    skip: int = 0,
    limit: Optional[int] = None,
    search: Optional[str] = None,
) -> tuple[list[dict], int]:
    """Lista distinct Prestamo.concesionario con id sintético."""
    col = Prestamo.concesionario
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
            "nombre": name,
            "activo": True,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        for i, name in enumerate(rows)
    ]
    return items, total


@router.get("", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
def listar_concesionarios(
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(1000, ge=1, le=5000),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Lista concesionarios desde distinct Prestamo.concesionario (solo lectura)."""
    items, total = _concesionarios_from_db(db, skip=skip, limit=limit, search=search)
    page_size = limit or 1000
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    page = (skip // page_size) + 1 if page_size else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": page_size,
        "pages": total_pages,
    }


@router.get("/activos", response_model=list)
def listar_concesionarios_activos(db: Session = Depends(get_db)):
    """Lista concesionarios activos (distinct Prestamo.concesionario) para formularios y dropdowns."""
    items, _ = _concesionarios_from_db(db, skip=0, limit=5000)
    return items


@router.get("/{concesionario_id}")
def obtener_concesionario(concesionario_id: int, db: Session = Depends(get_db)):
    """Por ahora no hay tabla concesionarios; devolver 501."""
    raise HTTPException(status_code=501, detail="CRUD de concesionarios no implementado (solo lectura desde préstamos)")


@router.post("")
def crear_concesionario(db: Session = Depends(get_db)):
    """Por ahora no hay tabla concesionarios; devolver 501."""
    raise HTTPException(status_code=501, detail="CRUD de concesionarios no implementado (solo lectura desde préstamos)")


@router.put("/{concesionario_id}")
def actualizar_concesionario(concesionario_id: int, db: Session = Depends(get_db)):
    """Por ahora no hay tabla concesionarios; devolver 501."""
    raise HTTPException(status_code=501, detail="CRUD de concesionarios no implementado (solo lectura desde préstamos)")


@router.delete("/{concesionario_id}")
def eliminar_concesionario(concesionario_id: int, db: Session = Depends(get_db)):
    """Por ahora no hay tabla concesionarios; devolver 501."""
    raise HTTPException(status_code=501, detail="CRUD de concesionarios no implementado (solo lectura desde préstamos)")
