"""
Endpoints de analistas. Lectura desde BD: distinct Prestamo.analista.
Sin tabla analista: listado y activos desde préstamos.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.prestamo import Prestamo

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=dict)
def listar_analistas(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Lista paginada de analistas (distinct Prestamo.analista), compatible con frontend.
    """
    safe_skip = max(skip, 0)
    safe_limit = max(min(limit, 1000), 1)

    base_q = (
        select(Prestamo.analista)
        .where(Prestamo.analista.isnot(None), Prestamo.analista != "")
    )
    if search:
        base_q = base_q.where(func.lower(Prestamo.analista).like(f"%{search.strip().lower()}%"))

    distinct_subq = base_q.distinct().subquery()
    total = db.execute(select(func.count()).select_from(distinct_subq)).scalar_one()

    rows = db.execute(
        select(distinct_subq.c.analista)
        .order_by(distinct_subq.c.analista)
        .offset(safe_skip)
        .limit(safe_limit)
    ).scalars().all()

    now_iso = datetime.now(timezone.utc).isoformat()
    items = [
        {
            "id": safe_skip + idx + 1,
            "nombre": name,
            "activo": True,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        for idx, name in enumerate(rows)
    ]

    page = (safe_skip // safe_limit) + 1
    pages = (total + safe_limit - 1) // safe_limit if total else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": safe_limit,
        "pages": pages,
    }


@router.get("/activos", response_model=list)
def listar_analistas_activos(db: Session = Depends(get_db)):
    """
    Lista analistas activos (distinct Prestamo.analista) para formularios y dropdowns.
    Devuelve lista con id sintético, nombre (analista), activo=True.
    """
    q = (
        select(Prestamo.analista)
        .where(Prestamo.analista.isnot(None), Prestamo.analista != "")
        .distinct()
        .order_by(Prestamo.analista)
    )
    rows = db.execute(q).scalars().all()
    now_iso = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": i + 1,
            "nombre": name,
            "activo": True,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        for i, name in enumerate(rows)
    ]
