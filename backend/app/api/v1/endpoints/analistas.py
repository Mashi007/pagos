"""
Endpoints de analistas. Lectura desde BD: distinct Prestamo.analista.
Sin tabla analista: listado y activos desde préstamos.
Eliminar/ desactivar = reasignar Prestamo.analista a un marcador (columna NOT NULL).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.prestamo import Prestamo

router = APIRouter(dependencies=[Depends(get_current_user)])

# Valor interno para “sin analista” (evita NULL; distinct sigue siendo un solo valor).
ANALISTA_PLACEHOLDER = "— Sin analista —"


def _nombre_analista_por_id_ordenado(db: Session, analista_id: int) -> str | None:
    """Índice 1..N en la lista ordenada de nombres distintos (misma lógica que el listado)."""
    if analista_id < 1:
        return None
    q = (
        select(Prestamo.analista)
        .where(Prestamo.analista.isnot(None), Prestamo.analista != "")
        .distinct()
        .order_by(Prestamo.analista)
        .offset(analista_id - 1)
        .limit(1)
    )
    return db.execute(q).scalar_one_or_none()


def _reasignar_analista_a_placeholder(db: Session, nombre: str) -> dict:
    stmt = (
        update(Prestamo)
        .where(Prestamo.analista == nombre)
        .values(analista=ANALISTA_PLACEHOLDER, analista_id=None)
    )
    result = db.execute(stmt)
    db.commit()
    n = result.rowcount or 0
    return {"message": f"Analista reasignado en {n} préstamo(s)", "afectados": n}


class AnalistaUpdateBody(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=255)
    activo: bool | None = None


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


@router.post("/importar")
def importar_analistas_desde_excel():
    """Sin tabla de catálogo: la importación masiva no aplica igual que otros módulos."""
    raise HTTPException(
        status_code=501,
        detail="Importación de catálogo no disponible: los analistas se toman de préstamos. Use carga o edición de préstamos.",
    )


@router.post("")
def crear_analista_catalogo():
    """No hay tabla analistas; el nombre surge al crear/editar préstamos."""
    raise HTTPException(
        status_code=501,
        detail="No existe catálogo independiente de analistas. Asigne el analista al crear o editar un préstamo.",
    )


@router.get("/{analista_id}", response_model=dict)
def obtener_analista(analista_id: int, db: Session = Depends(get_db)):
    nombre = _nombre_analista_por_id_ordenado(db, analista_id)
    if not nombre:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": analista_id,
        "nombre": nombre,
        "activo": True,
        "created_at": now_iso,
        "updated_at": now_iso,
    }


@router.put("/{analista_id}", response_model=dict)
def actualizar_analista(
    analista_id: int,
    body: AnalistaUpdateBody,
    db: Session = Depends(get_db),
):
    old = _nombre_analista_por_id_ordenado(db, analista_id)
    if not old:
        raise HTTPException(status_code=404, detail="Analista no encontrado")

    if body.activo is False:
        if old == ANALISTA_PLACEHOLDER:
            raise HTTPException(status_code=400, detail="Este valor ya está inactivo a nivel sistema")
        out = _reasignar_analista_a_placeholder(db, old)
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "id": analista_id,
            "nombre": ANALISTA_PLACEHOLDER,
            "activo": False,
            "created_at": now_iso,
            "updated_at": now_iso,
            "message": out["message"],
            "afectados": out["afectados"],
        }

    if body.nombre is not None:
        new = body.nombre.strip()
        if not new:
            raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
        if new == old:
            now_iso = datetime.now(timezone.utc).isoformat()
            return {
                "id": analista_id,
                "nombre": old,
                "activo": True,
                "created_at": now_iso,
                "updated_at": now_iso,
                "message": "Sin cambios",
            }
        stmt = (
            update(Prestamo)
            .where(Prestamo.analista == old)
            .values(analista=new)
        )
        result = db.execute(stmt)
        db.commit()
        n = result.rowcount or 0
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "id": analista_id,
            "nombre": new,
            "activo": True,
            "created_at": now_iso,
            "updated_at": now_iso,
            "message": f"Renombrado en {n} préstamo(s)",
            "afectados": n,
        }

    raise HTTPException(
        status_code=400,
        detail="Indique un nombre nuevo o desactive el analista (activo=false)",
    )


@router.delete("/{analista_id}", response_model=dict)
def eliminar_analista(analista_id: int, db: Session = Depends(get_db)):
    old = _nombre_analista_por_id_ordenado(db, analista_id)
    if not old:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    if old == ANALISTA_PLACEHOLDER:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar el marcador de sistema",
        )
    out = _reasignar_analista_a_placeholder(db, old)
    return {"message": out["message"], "afectados": out["afectados"]}
