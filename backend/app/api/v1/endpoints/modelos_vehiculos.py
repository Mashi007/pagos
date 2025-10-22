# backend/app/api/v1/endpoints/modelos_vehiculos.py
"""
Endpoints para gestión de modelos de vehículos
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from app.db.session import get_db
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.modelo_vehiculo import (
    ModeloVehiculoCreate,
    ModeloVehiculoUpdate,
    ModeloVehiculoResponse,
    ModeloVehiculoListResponse
)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=ModeloVehiculoListResponse)
def listar_modelos_vehiculos(
    # Paginación
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(20, ge=1, le=1000, description="Tamaño de página"),

    # Búsqueda
    search: Optional[str] = Query(None, description="Buscar en modelo"),

    # Filtros
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📋 Listar modelos de vehículos con paginación y filtros
    """
    try:
        # Construir query base
        query = db.query(ModeloVehiculo)

        # Aplicar filtros
        if search:
            query = query.filter(
                or_(
                    ModeloVehiculo.modelo.ilike(f"%{search}%")
                )
            )

        if activo is not None:
            query = query.filter(ModeloVehiculo.activo == activo)

        # Ordenar por modelo
        query = query.order_by(ModeloVehiculo.modelo)

        # Contar total
        total = query.count()

        # Paginación
        offset = (page - 1) * limit
        modelos = query.offset(offset).limit(limit).all()

        # Serializar respuesta
        modelos_response = [
            ModeloVehiculoResponse.model_validate(modelo) 
            for modelo in modelos
        ]

        return ModeloVehiculoListResponse(
            items=modelos_response,
            total=total,
            page=page,
            page_size=limit,
            total_pages=(total + limit - 1) // limit
        )

    except Exception as e:
        logger.error(f"Error listando modelos de vehículos: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/activos", response_model=List[ModeloVehiculoResponse])
def listar_modelos_activos(
    db: Session = Depends(get_db)
    # TEMPORALMENTE SIN AUTENTICACIÓN PARA DROPDOWNS
    # current_user: User = Depends(get_current_user)
):
    """
    📋 Listar solo modelos de vehículos activos (para formularios)
    """
    try:
        modelos = db.query(ModeloVehiculo).filter(
            ModeloVehiculo.activo == True
        ).order_by(ModeloVehiculo.modelo).all()

        return [
            ModeloVehiculoResponse.model_validate(modelo) 
            for modelo in modelos
        ]

    except Exception as e:
        logger.error(f"Error listando modelos activos: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{modelo_id}", response_model=ModeloVehiculoResponse)
def obtener_modelo_vehiculo(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Obtener un modelo de vehículo por ID
    """
    try:
        modelo = db.query(ModeloVehiculo).filter(
            ModeloVehiculo.id == modelo_id
        ).first()

        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")

        return ModeloVehiculoResponse.model_validate(modelo)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo modelo {modelo_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/", response_model=ModeloVehiculoResponse)
def crear_modelo_vehiculo(
    modelo_data: ModeloVehiculoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ➕ Crear un nuevo modelo de vehículo
    """
    try:
        # Verificar si ya existe un modelo con el mismo nombre
        existing_modelo = db.query(ModeloVehiculo).filter(
            ModeloVehiculo.modelo.ilike(modelo_data.modelo)
        ).first()

        if existing_modelo:
            raise HTTPException(
                status_code=400, 
                detail="Ya existe un modelo de vehículo con ese nombre"
            )

        # Crear nuevo modelo
        nuevo_modelo = ModeloVehiculo(
            modelo=modelo_data.modelo.strip(),
            activo=modelo_data.activo
        )

        db.add(nuevo_modelo)
        db.commit()
        db.refresh(nuevo_modelo)

        logger.info(f"Modelo de vehículo creado: {nuevo_modelo.modelo} (ID: {nuevo_modelo.id})")

        return ModeloVehiculoResponse.model_validate(nuevo_modelo)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando modelo de vehículo: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.put("/{modelo_id}", response_model=ModeloVehiculoResponse)
def actualizar_modelo_vehiculo(
    modelo_id: int,
    modelo_data: ModeloVehiculoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ✏️ Actualizar un modelo de vehículo existente
    """
    try:
        # Buscar modelo existente
        modelo = db.query(ModeloVehiculo).filter(
            ModeloVehiculo.id == modelo_id
        ).first()

        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")

        # Verificar nombre único si se está cambiando
        if modelo_data.modelo and modelo_data.modelo != modelo.modelo:
            existing_modelo = db.query(ModeloVehiculo).filter(
                ModeloVehiculo.modelo.ilike(modelo_data.modelo),
                ModeloVehiculo.id != modelo_id
            ).first()

            if existing_modelo:
                raise HTTPException(
                    status_code=400, 
                    detail="Ya existe un modelo de vehículo con ese nombre"
                )

        # Actualizar campos
        if modelo_data.modelo is not None:
            modelo.modelo = modelo_data.modelo.strip()
        if modelo_data.activo is not None:
            modelo.activo = modelo_data.activo

        db.commit()
        db.refresh(modelo)

        logger.info(f"Modelo de vehículo actualizado: {modelo.modelo} (ID: {modelo.id})")

        return ModeloVehiculoResponse.model_validate(modelo)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando modelo {modelo_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.delete("/{modelo_id}")
def eliminar_modelo_vehiculo(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🗑️ Eliminar un modelo de vehículo (HARD DELETE - borrado completo de BD)
    """
    try:
        # Buscar modelo existente
        modelo = db.query(ModeloVehiculo).filter(
            ModeloVehiculo.id == modelo_id
        ).first()

        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")

        # HARD DELETE - eliminar completamente de la base de datos
        modelo_nombre = modelo.modelo  # Guardar nombre para log
        db.delete(modelo)
        db.commit()

        logger.info(f"Modelo de vehículo ELIMINADO COMPLETAMENTE: {modelo_nombre} (ID: {modelo_id})")

        return {"message": "Modelo de vehículo eliminado completamente de la base de datos"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando modelo {modelo_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
