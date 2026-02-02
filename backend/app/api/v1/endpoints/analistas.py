"""
Endpoints de analistas. Lectura desde BD: distinct Prestamo.analista.
Sin tabla analista: listado y activos desde préstamos; CRUD devuelve 501.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.prestamo import Prestamo

router = APIRouter(dependencies=[Depends(get_current_user)])


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
