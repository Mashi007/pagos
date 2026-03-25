"""
Catálogo de analistas (tabla analistas). Gestionar en /pagos/analistas.
Los préstamos enlazan con analista_id y mantienen prestamos.analista alineado al nombre del catálogo.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.analista import Analista
from app.models.prestamo import Prestamo

router = APIRouter(dependencies=[Depends(get_current_user)])

ANALISTA_PLACEHOLDER = "— Sin analista —"


class AnalistaCreateBody(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    activo: bool = True


class AnalistaUpdateBody(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=255)
    activo: bool | None = None


def _row_to_item(a: Analista) -> dict:
    return {
        "id": a.id,
        "nombre": a.nombre,
        "activo": a.activo,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


@router.get("", response_model=dict)
def listar_analistas(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    safe_skip = max(skip, 0)
    safe_limit = max(min(limit, 1000), 1)
    count_q = select(func.count()).select_from(Analista)
    q = select(Analista)
    if search and search.strip():
        like = f"%{search.strip()}%"
        q = q.where(Analista.nombre.ilike(like))
        count_q = count_q.where(Analista.nombre.ilike(like))
    total = db.scalar(count_q) or 0
    q = q.order_by(Analista.nombre).offset(safe_skip).limit(safe_limit)
    rows = db.execute(q).scalars().all()
    items = [_row_to_item(a) for a in rows]
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
    q = (
        select(Analista)
        .where(Analista.activo.is_(True))
        .order_by(Analista.nombre)
    )
    rows = db.execute(q).scalars().all()
    return [_row_to_item(a) for a in rows]


@router.post("/importar")
def importar_analistas_desde_excel():
    raise HTTPException(
        status_code=501,
        detail="Importación masiva pendiente; cree analistas con POST o desde la pantalla.",
    )


@router.post("", response_model=dict)
def crear_analista(body: AnalistaCreateBody, db: Session = Depends(get_db)):
    n = body.nombre.strip()
    row = Analista(nombre=n, activo=body.activo)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un analista con ese nombre")
    db.refresh(row)
    return _row_to_item(row)


@router.get("/{analista_id}", response_model=dict)
def obtener_analista(analista_id: int, db: Session = Depends(get_db)):
    row = db.get(Analista, analista_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    return _row_to_item(row)


@router.put("/{analista_id}", response_model=dict)
def actualizar_analista(
    analista_id: int,
    body: AnalistaUpdateBody,
    db: Session = Depends(get_db),
):
    row = db.get(Analista, analista_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analista no encontrado")

    if body.nombre is None and body.activo is None:
        raise HTTPException(
            status_code=400,
            detail="Indique nombre nuevo y/o activo (true/false)",
        )

    messages: list[str] = []
    old = row.nombre

    if body.nombre is not None:
        new = body.nombre.strip()
        if not new:
            raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
        if new != old:
            row.nombre = new
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                raise HTTPException(status_code=409, detail="Ese nombre ya está en uso en el catálogo")
            db.execute(
                update(Prestamo)
                .where(Prestamo.analista_id == analista_id)
                .values(analista=new)
            )
            db.execute(
                update(Prestamo)
                .where(
                    Prestamo.analista_id.is_(None),
                    Prestamo.analista == old,
                )
                .values(analista=new)
            )
            messages.append("Nombre y préstamos vinculados actualizados")
        else:
            messages.append("Sin cambios de nombre")

    if body.activo is not None:
        row.activo = body.activo
        messages.append("Desactivado" if not body.activo else "Reactivado")

    db.commit()
    db.refresh(row)
    return {**_row_to_item(row), "message": "; ".join(messages)}


@router.delete("/{analista_id}", response_model=dict)
def eliminar_analista(analista_id: int, db: Session = Depends(get_db)):
    row = db.get(Analista, analista_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    if row.nombre == ANALISTA_PLACEHOLDER:
        raise HTTPException(status_code=400, detail="No se puede eliminar el marcador de sistema")

    db.execute(
        update(Prestamo)
        .where(Prestamo.analista_id == analista_id)
        .values(analista=ANALISTA_PLACEHOLDER, analista_id=None)
    )
    db.execute(
        update(Prestamo)
        .where(Prestamo.analista_id.is_(None), Prestamo.analista == row.nombre)
        .values(analista=ANALISTA_PLACEHOLDER)
    )
    db.delete(row)
    db.commit()
    return {"message": "Analista eliminado; préstamos afectados pasaron a marcador sin analista"}
