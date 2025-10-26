import logging
import traceback
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.concesionario import Concesionario
from app.models.user import User
from app.schemas.concesionario import (
    ConcesionarioCreate,
    ConcesionarioListResponse,
    ConcesionarioResponse,
    ConcesionarioUpdate,
)

# Endpoints de gestion de concesionarios


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/test-no-auth")
def test_no_auth():
    # Test endpoint sin autenticacion
    try:
        logger.info("Test endpoint sin autenticacion")
        return {"message": "Test exitoso sin autenticacion"}
    except Exception as e:
        logger.error(f"Error en test_no_auth: {e}")
        return {"error": "Error interno"}


@router.get("/test-simple")
def test_simple():
    # Test endpoint simple
    try:
        logger.info("Test endpoint simple")
        return {"message": "Test simple exitoso"}
    except Exception:
        return {"error": "Error interno"}


@router.get("/test-auth")
def test_auth(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Test endpoint con autenticacion
    try:
        logger.info(f"Test endpoint con autenticacion - Usuario: {current_user.email}")
        return {"message": "Test exitoso con autenticacion", "user": current_user.email}
    except Exception as e:
        logger.error(f"Error en test_auth: {e}")
        return {"error": "Error interno"}


@router.get("/list-no-auth")
def list_concesionarios_no_auth(
    limit: int = Query(20, ge=1, le=1000, description="Limite de resultados"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
):
    # Listar concesionarios sin autenticacion
    try:
        query = db.query(Concesionario)

        if activo is not None:
            query = query.filter(Concesionario.activo == activo)
        if search:
            query = query.filter(Concesionario.nombre.ilike(f"%{search}%"))

        # Ordenar por ID
        query = query.order_by(Concesionario.id)

        # Obtener total
        total = query.count()

        # Aplicar paginacion
        concesionarios = query.limit(limit).all()

        # Calcular paginas
        pages = (total + limit - 1) // limit

        return {
            "concesionarios": [c.to_dict() for c in concesionarios],
            "total": total,
            "pages": pages,
        }
    except Exception as e:
        logger.error(f"Error en list_concesionarios_no_auth: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/", response_model=ConcesionarioListResponse)
def list_concesionarios(
    limit: int = Query(20, ge=1, le=1000, description="Limite de resultados"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar concesionarios con autenticacion
    try:
        query = db.query(Concesionario)

        if activo is not None:
            query = query.filter(Concesionario.activo == activo)
        if search:
            query = query.filter(Concesionario.nombre.ilike(f"%{search}%"))

        # Ordenar por ID
        query = query.order_by(Concesionario.id)

        # Obtener total
        total = query.count()

        # Aplicar paginacion
        concesionarios = query.limit(limit).all()

        # Calcular paginas
        pages = (total + limit - 1) // limit

        return ConcesionarioListResponse(
            items=[c.to_dict() for c in concesionarios],
            total=total,
            page=1,
            size=limit,
            pages=pages,
        )
    except Exception as e:
        logger.error(f"Error en list_concesionarios: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/activos")
def list_concesionarios_activos(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Listar solo concesionarios activos (para formularios)."""
    concesionarios = (
        db.query(Concesionario).filter(Concesionario.activo.is_(True)).all()
    )
    return [c.to_dict() for c in concesionarios]


@router.get("/dropdown")
def get_concesionarios_dropdown(
    db: Session = Depends(get_db),
    # TEMPORALMENTE SIN AUTENTICACION PARA DROPDOWNS
    # current_user: User = Depends(get_current_user)
):
    # Obtener concesionarios activos para dropdown
    try:
        concesionarios = db.query(Concesionario).filter(Concesionario.activo).all()
        return [{"id": c.id, "nombre": c.nombre} for c in concesionarios]
    except Exception as e:
        logger.error(f"Error en get_concesionarios_dropdown: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{concesionario_id}", response_model=ConcesionarioResponse)
def obtener_concesionario(
    concesionario_id: int = Path(..., description="ID del concesionario"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener un concesionario por ID
    concesionario = (
        db.query(Concesionario).filter(Concesionario.id == concesionario_id).first()
    )
    if not concesionario:
        raise HTTPException(status_code=404, detail="Concesionario no encontrado")
    return ConcesionarioResponse.model_validate(concesionario)


@router.post("/", response_model=ConcesionarioResponse)
def crear_concesionario(
    concesionario_data: ConcesionarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear un nuevo concesionario
    try:
        # Crear nuevo concesionario
        concesionario = Concesionario(**concesionario_data.model_dump())

        db.add(concesionario)
        db.commit()
        db.refresh(concesionario)

        logger.info(f"Concesionario creado: ID={concesionario.id}")
        return ConcesionarioResponse.model_validate(concesionario)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando concesionario: {e}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al crear concesionario: {str(e)}"
        )


@router.put("/{concesionario_id}", response_model=ConcesionarioResponse)
def actualizar_concesionario(
    concesionario_id: int = Path(..., description="ID del concesionario"),
    concesionario_data: ConcesionarioUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar un concesionario existente
    try:
        concesionario = (
            db.query(Concesionario).filter(Concesionario.id == concesionario_id).first()
        )
        if not concesionario:
            raise HTTPException(status_code=404, detail="Concesionario no encontrado")

        # Verificar nombre unico si se esta cambiando
        if (
            concesionario_data.nombre
            and concesionario_data.nombre != concesionario.nombre
        ):
            existing = (
                db.query(Concesionario)
                .filter(Concesionario.nombre == concesionario_data.nombre)
                .first()
            )
            if existing:
                raise HTTPException(status_code=400, detail="El nombre ya existe")

        update_data = concesionario_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(concesionario, field, value)

        # Actualizar timestamp manually
        concesionario.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(concesionario)
        return ConcesionarioResponse.model_validate(concesionario)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar concesionario: {str(e)}",
        )


@router.delete("/{concesionario_id}")
def eliminar_concesionario(
    concesionario_id: int = Path(..., description="ID del concesionario"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar un concesionario (HARD DELETE - borrado completo de BD)
    try:
        concesionario = (
            db.query(Concesionario).filter(Concesionario.id == concesionario_id).first()
        )
        if not concesionario:
            raise HTTPException(status_code=404, detail="Concesionario no encontrado")

        db.delete(concesionario)
        db.commit()

        return {"message": "Concesionario eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar concesionario: {str(e)}",
        )
