# backend/app/api/v1/endpoints/modelos_vehiculos.py
"""
Endpoints para gestión de modelos de vehículos configurables
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.user import User
from app.schemas.modelo_vehiculo import (
    ModeloVehiculoCreate, 
    ModeloVehiculoUpdate, 
    ModeloVehiculoResponse,
    ModeloVehiculoListResponse,
    ModeloVehiculoActivosResponse,
    ModeloVehiculoStatsResponse
)
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=ModeloVehiculoListResponse)
def listar_modelos_vehiculos(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a retornar"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    marca: Optional[str] = Query(None, description="Filtrar por marca"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📋 Listar todos los modelos de vehículos con paginación y filtros
    """
    try:
        query = db.query(ModeloVehiculo)
        
        # Aplicar filtros
        if activo is not None:
            query = query.filter(ModeloVehiculo.activo == activo)
        
        if marca:
            query = query.filter(ModeloVehiculo.marca.ilike(f"%{marca}%"))
        
        if categoria:
            query = query.filter(ModeloVehiculo.categoria == categoria)
        
        if search:
            query = query.filter(
                ModeloVehiculo.nombre_completo.ilike(f"%{search}%") |
                ModeloVehiculo.marca.ilike(f"%{search}%") |
                ModeloVehiculo.modelo.ilike(f"%{search}%")
            )
        
        # Obtener total
        total = query.count()
        
        # Aplicar paginación
        modelos = query.order_by(ModeloVehiculo.marca, ModeloVehiculo.modelo).offset(skip).limit(limit).all()
        
        # Calcular páginas
        pages = (total + limit - 1) // limit
        
        return ModeloVehiculoListResponse(
            items=[ModeloVehiculoResponse.from_orm(m) for m in modelos],
            total=total,
            page=(skip // limit) + 1,
            page_size=limit,
            total_pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar modelos de vehículos: {str(e)}")


@router.get("/activos", response_model=List[ModeloVehiculoActivosResponse])
def listar_modelos_activos(
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    marca: Optional[str] = Query(None, description="Filtrar por marca"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🚗 Listar solo modelos activos (para formularios)
    """
    try:
        query = db.query(ModeloVehiculo).filter(ModeloVehiculo.activo == True)
        
        if categoria:
            query = query.filter(ModeloVehiculo.categoria == categoria)
        
        if marca:
            query = query.filter(ModeloVehiculo.marca == marca)
        
        modelos = query.order_by(ModeloVehiculo.marca, ModeloVehiculo.modelo).all()
        return [ModeloVehiculoActivosResponse.from_orm(m) for m in modelos]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar modelos activos: {str(e)}")


@router.post("/", response_model=ModeloVehiculoResponse, status_code=201)
def crear_modelo_vehiculo(
    modelo_data: ModeloVehiculoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ➕ Crear un nuevo modelo de vehículo
    """
    # Solo admin puede crear modelos
    if current_user.rol not in ["ADMIN", "GERENTE"]:
        raise HTTPException(
            status_code=403, 
            detail="Solo administradores y gerentes pueden crear modelos de vehículos"
        )
    
    try:
        # Verificar que no existe ya
        existing = db.query(ModeloVehiculo).filter(
            ModeloVehiculo.nombre_completo == modelo_data.nombre_completo
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Ya existe un modelo con este nombre completo"
            )
        
        # Crear el modelo
        modelo = ModeloVehiculo(**modelo_data.dict())
        db.add(modelo)
        db.commit()
        db.refresh(modelo)
        
        return ModeloVehiculoResponse.from_orm(modelo)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando modelo de vehículo: {str(e)}")


@router.get("/{modelo_id}", response_model=ModeloVehiculoResponse)
def obtener_modelo_vehiculo(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Obtener un modelo de vehículo por ID
    """
    modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == modelo_id).first()
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")
    
    return ModeloVehiculoResponse.from_orm(modelo)


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
    # Solo admin puede actualizar modelos
    if current_user.rol not in ["ADMIN", "GERENTE"]:
        raise HTTPException(
            status_code=403, 
            detail="Solo administradores y gerentes pueden actualizar modelos de vehículos"
        )
    
    try:
        modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == modelo_id).first()
        
        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")
        
        # Verificar nombre único si se está cambiando
        if modelo_data.nombre_completo and modelo_data.nombre_completo != modelo.nombre_completo:
            existing = db.query(ModeloVehiculo).filter(
                ModeloVehiculo.nombre_completo == modelo_data.nombre_completo,
                ModeloVehiculo.id != modelo_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail="Ya existe un modelo con este nombre completo"
                )
        
        # Actualizar campos
        update_data = modelo_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(modelo, field, value)
        
        db.commit()
        db.refresh(modelo)
        
        return ModeloVehiculoResponse.from_orm(modelo)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando modelo de vehículo: {str(e)}")


@router.delete("/{modelo_id}")
def eliminar_modelo_vehiculo(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🗑️ Eliminar un modelo de vehículo (soft delete - marcar como inactivo)
    """
    # Solo admin puede eliminar modelos
    if current_user.rol not in ["ADMIN", "GERENTE"]:
        raise HTTPException(
            status_code=403, 
            detail="Solo administradores y gerentes pueden eliminar modelos de vehículos"
        )
    
    try:
        modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == modelo_id).first()
        
        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo de vehículo no encontrado")
        
        # Soft delete - marcar como inactivo
        modelo.activo = False
        db.commit()
        
        return {"message": "Modelo de vehículo desactivado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando modelo de vehículo: {str(e)}")


@router.get("/estadisticas/resumen", response_model=ModeloVehiculoStatsResponse)
def obtener_estadisticas_modelos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Obtener estadísticas de modelos de vehículos
    """
    try:
        # Estadísticas generales
        total_modelos = db.query(ModeloVehiculo).count()
        modelos_activos = db.query(ModeloVehiculo).filter(ModeloVehiculo.activo == True).count()
        modelos_inactivos = total_modelos - modelos_activos
        
        # Por categoría
        por_categoria = db.query(
            ModeloVehiculo.categoria,
            func.count(ModeloVehiculo.id).label('cantidad')
        ).filter(ModeloVehiculo.activo == True).group_by(ModeloVehiculo.categoria).all()
        
        # Por marca
        por_marca = db.query(
            ModeloVehiculo.marca,
            func.count(ModeloVehiculo.id).label('cantidad')
        ).filter(ModeloVehiculo.activo == True).group_by(ModeloVehiculo.marca).all()
        
        return ModeloVehiculoStatsResponse(
            total_modelos=total_modelos,
            modelos_activos=modelos_activos,
            modelos_inactivos=modelos_inactivos,
            por_categoria={cat: cant for cat, cant in por_categoria},
            por_marca={marca: cant for marca, cant in por_marca}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")


@router.get("/categorias/lista")
def listar_categorias_disponibles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📋 Listar todas las categorías disponibles
    """
    try:
        categorias = db.query(ModeloVehiculo.categoria).filter(
            ModeloVehiculo.categoria.isnot(None),
            ModeloVehiculo.activo == True
        ).distinct().all()
        
        return [cat[0] for cat in categorias if cat[0]]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando categorías: {str(e)}")


@router.get("/marcas/lista")
def listar_marcas_disponibles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🏷️ Listar todas las marcas disponibles
    """
    try:
        marcas = db.query(ModeloVehiculo.marca).filter(
            ModeloVehiculo.activo == True
        ).distinct().all()
        
        return [marca[0] for marca in marcas]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando marcas: {str(e)}")
