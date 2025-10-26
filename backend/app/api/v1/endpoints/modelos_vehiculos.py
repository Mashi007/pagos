import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.user import User
from app.schemas.modelo_vehiculo import (
    ModeloVehiculoCreate,
    ModeloVehiculoListResponse,
    ModeloVehiculoResponse,
    ModeloVehiculoUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=ModeloVehiculoListResponse)
def listar_modelos_vehiculos(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(20, ge=1, le=1000, description="Tamaño de página"),
    # Búsqueda
    search: Optional[str] = Query(None, description="Buscar por modelo"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar modelos de vehículos con filtros"""

    query = db.query(ModeloVehiculo)

    # Aplicar filtros
    if search:
        query = query.filter(or_(ModeloVehiculo.modelo.ilike(f"%{search}%")))

    if activo is not None:
        query = query.filter(ModeloVehiculo.activo == activo)

    # Ordenar por ID
    query = query.order_by(ModeloVehiculo.id)

    # Contar total
    total = query.count()

    # Paginar
    modelos = query.offset(skip).limit(limit).all()

    return ModeloVehiculoListResponse(
        items=modelos,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit,
    )


@router.get("/activos", response_model=List[ModeloVehiculoResponse])
def listar_modelos_activos(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Listar solo modelos activos (para formularios)."""
    modelos = db.query(ModeloVehiculo).filter(ModeloVehiculo.activo.is_(True)).all()
    return modelos


@router.get("/{modelo_id}", response_model=ModeloVehiculoResponse)
def obtener_modelo_vehiculo(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener un modelo de vehículo por ID"""

    modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == modelo_id).first()

    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")

    return modelo


@router.post("/", response_model=ModeloVehiculoResponse)
def crear_modelo_vehiculo(
    modelo_data: ModeloVehiculoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear un nuevo modelo de vehículo"""

    # Verificar si ya existe
    existing = (
        db.query(ModeloVehiculo)
        .filter(ModeloVehiculo.modelo == modelo_data.modelo)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400, detail="Ya existe un modelo con ese nombre"
        )

    modelo = ModeloVehiculo(**modelo_data.dict())
    db.add(modelo)
    db.commit()
    db.refresh(modelo)

    return modelo


@router.put("/{modelo_id}", response_model=ModeloVehiculoResponse)
def actualizar_modelo_vehiculo(
    modelo_id: int,
    modelo_data: ModeloVehiculoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar un modelo de vehículo"""

    modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == modelo_id).first()

    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")

    # Actualizar campos
    for field, value in modelo_data.dict(exclude_unset=True).items():
        setattr(modelo, field, value)

    # Actualizar timestamp manualmente
    modelo.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(modelo)

    return modelo


@router.delete("/{modelo_id}")
def eliminar_modelo_vehiculo(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar un modelo de vehículo"""

    modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == modelo_id).first()

    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")

    db.delete(modelo)
    db.commit()

    return {"message": "Modelo de vehículo eliminado exitosamente"}
