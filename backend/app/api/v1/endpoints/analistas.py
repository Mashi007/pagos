import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.analista import Analista
from app.models.user import User
from app.schemas.analista import AnalistaCreate, AnalistaResponse, AnalistaUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/test-no-auth")
def test_analistas_no_auth(db: Session = Depends(get_db)):
    # Test endpoint sin autenticación para verificar analistas
    try:
        total_analistas = db.query(Analista).count()
        analistas = db.query(Analista).limit(5).all()
        analistas_data = []

        for analista in analistas:
            analistas_data.append(
                {
                    "id": analista.id,
                    "nombre": analista.nombre,
                    "email": analista.email,
                    "activo": analista.activo,
                }
            )

        return {
            "message": "Test exitoso - Analistas",
            "total_analistas": total_analistas,
            "analistas_muestra": analistas_data,
        }

    except Exception as e:
        logger.error(f"Error en test_analistas_no_auth: {e}")
        return {"error": "Error interno"}


@router.get("/", response_model=List[AnalistaResponse])
def listar_analistas(
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar analistas con filtros
    try:
        query = db.query(Analista)

        if activo is not None:
            query = query.filter(Analista.activo == activo)

        analistas = query.all()
        return analistas

    except Exception as e:
        logger.error(f"Error listando analistas: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/{analista_id}", response_model=AnalistaResponse)
def obtener_analista(
    analista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener analista específico
    try:
        analista = db.query(Analista).filter(Analista.id == analista_id).first()

        if not analista:
            raise HTTPException(status_code=404, detail="Analista no encontrado")

        return analista

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo analista: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/", response_model=AnalistaResponse, status_code=status.HTTP_201_CREATED)
def crear_analista(
    analista_data: AnalistaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear nuevo analista
    try:
        # Verificar que no exista un analista con el mismo email
        analista_existente = (
            db.query(Analista).filter(Analista.email == analista_data.email).first()
        )

        if analista_existente:
            raise HTTPException(
                status_code=400, detail="Ya existe un analista con este email"
            )

        nuevo_analista = Analista(**analista_data.model_dump())

        db.add(nuevo_analista)
        db.commit()
        db.refresh(nuevo_analista)

        return nuevo_analista

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando analista: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.put("/{analista_id}", response_model=AnalistaResponse)
def actualizar_analista(
    analista_id: int,
    analista_data: AnalistaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar analista
    try:
        analista = db.query(Analista).filter(Analista.id == analista_id).first()

        if not analista:
            raise HTTPException(status_code=404, detail="Analista no encontrado")

        # Verificar email único si se está cambiando
        if analista_data.email and analista_data.email != analista.email:
            analista_existente = (
                db.query(Analista)
                .filter(
                    Analista.email == analista_data.email, Analista.id != analista_id
                )
                .first()
            )

            if analista_existente:
                raise HTTPException(
                    status_code=400, detail="Ya existe un analista con este email"
                )

        # Actualizar campos
        for field, value in analista_data.model_dump(exclude_unset=True).items():
            setattr(analista, field, value)

        db.commit()
        db.refresh(analista)

        return analista

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando analista: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.delete("/{analista_id}")
def eliminar_analista(
    analista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar analista
    try:
        asesor = db.query(Analista).filter(Analista.id == analista_id).first()

        if not asesor:
            raise HTTPException(status_code=404, detail="Analista no encontrado")

        db.delete(asesor)
        db.commit()
        return {"message": "Analista eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar analista: {str(e)}"
        )
