"""
Endpoints de gestión de concesionarios
CRUD completo para concesionarios
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.concesionario import Concesionario
from app.models.user import User
from app.schemas.concesionario import (
    ConcesionarioCreate, 
    ConcesionarioUpdate, 
    ConcesionarioResponse,
    ConcesionarioListResponse
)
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=ConcesionarioListResponse)
def listar_concesionarios(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a retornar"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📋 Listar todos los concesionarios con paginación y filtros
    """
    try:
        query = db.query(Concesionario)
        
        # Aplicar filtros
        if activo is not None:
            query = query.filter(Concesionario.activo == activo)
        
        if search:
            query = query.filter(Concesionario.nombre.ilike(f"%{search}%"))
        
        # Obtener total
        total = query.count()
        
        # Aplicar paginación
        concesionarios = query.offset(skip).limit(limit).all()
        
        # Calcular páginas
        pages = (total + limit - 1) // limit
        
        return ConcesionarioListResponse(
            items=[ConcesionarioResponse.model_validate(c) for c in concesionarios],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar concesionarios: {str(e)}")

@router.get("/activos")
def listar_concesionarios_activos(
    db: Session = Depends(get_db)
):
    """
    🏢 Listar solo concesionarios activos (para formularios)
    """
    try:
        concesionarios = db.query(Concesionario).filter(Concesionario.activo == True).all()
        return [c.to_dict() for c in concesionarios]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar concesionarios activos: {str(e)}")

@router.get("/{concesionario_id}", response_model=ConcesionarioResponse)
def obtener_concesionario(
    concesionario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Obtener un concesionario por ID
    """
    concesionario = db.query(Concesionario).filter(Concesionario.id == concesionario_id).first()
    
    if not concesionario:
        raise HTTPException(status_code=404, detail="Concesionario no encontrado")
    
    return ConcesionarioResponse.model_validate(concesionario)

@router.post("", response_model=ConcesionarioResponse)
def crear_concesionario(
    concesionario_data: ConcesionarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ➕ Crear un nuevo concesionario
    """
    try:
        # 🔍 DEBUG: Imprimir los datos recibidos
        print(f"📥 Concesionario recibido: {concesionario_data}")
        print(f"📥 Tipo: {type(concesionario_data)}")
        
        # Verificar que no exista un concesionario con el mismo nombre
        existing = db.query(Concesionario).filter(Concesionario.nombre == concesionario_data.nombre).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un concesionario con este nombre")
        
        # Limpiar campos vacíos
        concesionario_dict = concesionario_data.dict()
        for key, value in concesionario_dict.items():
            if value == "" or value is None:
                concesionario_dict[key] = None
        
        print(f"📦 Dict limpio: {concesionario_dict}")
        
        # Crear nuevo concesionario
        concesionario = Concesionario(**concesionario_dict)
        db.add(concesionario)
        db.commit()
        db.refresh(concesionario)
        
        print(f"✅ Concesionario creado: ID={concesionario.id}")
        return ConcesionarioResponse.model_validate(concesionario)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creando concesionario: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear concesionario: {str(e)}")

@router.put("/{concesionario_id}", response_model=ConcesionarioResponse)
def actualizar_concesionario(
    concesionario_id: int,
    concesionario_data: ConcesionarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ✏️ Actualizar un concesionario existente
    """
    try:
        concesionario = db.query(Concesionario).filter(Concesionario.id == concesionario_id).first()
        
        if not concesionario:
            raise HTTPException(status_code=404, detail="Concesionario no encontrado")
        
        # Verificar nombre único si se está cambiando
        if concesionario_data.nombre and concesionario_data.nombre != concesionario.nombre:
            existing = db.query(Concesionario).filter(
                Concesionario.nombre == concesionario_data.nombre,
                Concesionario.id != concesionario_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Ya existe un concesionario con este nombre")
        
        # Actualizar campos
        update_data = concesionario_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(concesionario, field, value)
        
        db.commit()
        db.refresh(concesionario)
        
        return ConcesionarioResponse.model_validate(concesionario)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar concesionario: {str(e)}")

@router.delete("/{concesionario_id}")
def eliminar_concesionario(
    concesionario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🗑️ Eliminar un concesionario (soft delete - marcar como inactivo)
    """
    try:
        concesionario = db.query(Concesionario).filter(Concesionario.id == concesionario_id).first()
        
        if not concesionario:
            raise HTTPException(status_code=404, detail="Concesionario no encontrado")
        
        # Soft delete - marcar como inactivo
        concesionario.activo = False
        db.commit()
        
        return {"message": "Concesionario eliminado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar concesionario: {str(e)}")
