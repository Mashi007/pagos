"""
Catálogo de concesionarios (tabla concesionarios). Gestionar en /pagos/concesionarios.
Los préstamos enlazan con concesionario_id y mantienen prestamos.concesionario alineado al nombre del catálogo.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.concesionario import Concesionario
from app.models.prestamo import Prestamo
from app.services.concesionarios_catalogo_sync import (
    sincronizar_concesionarios_desde_prestamos_si_catalogo_vacio,
)

router = APIRouter(dependencies=[Depends(get_current_user)])

CONCESIONARIO_PLACEHOLDER = "— Sin concesionario —"


class ConcesionarioCreateBody(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    activo: bool = True


class ConcesionarioUpdateBody(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=255)
    activo: bool | None = None


def _row_to_item(c: Concesionario) -> dict:
    return {
        "id": c.id,
        "nombre": c.nombre,
        "activo": c.activo,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("", response_model=dict)
def listar_concesionarios(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    sincronizar_concesionarios_desde_prestamos_si_catalogo_vacio(db)
    safe_skip = max(skip, 0)
    safe_limit = max(min(limit, 1000), 1)
    count_q = select(func.count()).select_from(Concesionario)
    q = select(Concesionario)
    if search and search.strip():
        like = f"%{search.strip()}%"
        q = q.where(Concesionario.nombre.ilike(like))
        count_q = count_q.where(Concesionario.nombre.ilike(like))
    total = db.scalar(count_q) or 0
    q = q.order_by(Concesionario.nombre).offset(safe_skip).limit(safe_limit)
    rows = db.execute(q).scalars().all()
    items = [_row_to_item(c) for c in rows]
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
def listar_concesionarios_activos(db: Session = Depends(get_db)):
    sincronizar_concesionarios_desde_prestamos_si_catalogo_vacio(db)
    q = (
        select(Concesionario)
        .where(Concesionario.activo.is_(True))
        .order_by(Concesionario.nombre)
    )
    rows = db.execute(q).scalars().all()
    return [_row_to_item(c) for c in rows]


@router.post("/importar")
def importar_concesionarios_desde_excel():
    raise HTTPException(
        status_code=501,
        detail="Importación masiva pendiente; cree concesionarios con POST o desde la pantalla.",
    )


@router.post("", response_model=dict)
def crear_concesionario(body: ConcesionarioCreateBody, db: Session = Depends(get_db)):
    n = body.nombre.strip()
    if not n:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    row = Concesionario(nombre=n, activo=body.activo)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un concesionario con ese nombre")
    db.refresh(row)
    return _row_to_item(row)


@router.get("/{concesionario_id}", response_model=dict)
def obtener_concesionario(concesionario_id: int, db: Session = Depends(get_db)):
    row = db.get(Concesionario, concesionario_id)
    if not row:
        raise HTTPException(status_code=404, detail="Concesionario no encontrado")
    return _row_to_item(row)


@router.put("/{concesionario_id}", response_model=dict)
def actualizar_concesionario(
    concesionario_id: int,
    body: ConcesionarioUpdateBody,
    db: Session = Depends(get_db),
):
    row = db.get(Concesionario, concesionario_id)
    if not row:
        raise HTTPException(status_code=404, detail="Concesionario no encontrado")

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
                raise HTTPException(
                    status_code=409,
                    detail="Ese nombre ya está en uso en el catálogo",
                )
            db.execute(
                update(Prestamo)
                .where(Prestamo.concesionario_id == concesionario_id)
                .values(concesionario=new)
            )
            db.execute(
                update(Prestamo)
                .where(
                    Prestamo.concesionario_id.is_(None),
                    Prestamo.concesionario == old,
                )
                .values(concesionario=new)
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


@router.delete("/{concesionario_id}", response_model=dict)
def eliminar_concesionario(concesionario_id: int, db: Session = Depends(get_db)):
    row = db.get(Concesionario, concesionario_id)
    if not row:
        raise HTTPException(status_code=404, detail="Concesionario no encontrado")
    if row.nombre == CONCESIONARIO_PLACEHOLDER:
        raise HTTPException(status_code=400, detail="No se puede eliminar el marcador de sistema")

    db.execute(
        update(Prestamo)
        .where(Prestamo.concesionario_id == concesionario_id)
        .values(concesionario=CONCESIONARIO_PLACEHOLDER, concesionario_id=None)
    )
    db.execute(
        update(Prestamo)
        .where(
            Prestamo.concesionario_id.is_(None),
            Prestamo.concesionario == row.nombre,
        )
        .values(concesionario=CONCESIONARIO_PLACEHOLDER)
    )
    db.delete(row)
    db.commit()
    return {
        "message": "Concesionario eliminado; préstamos afectados pasaron a marcador sin concesionario"
    }
