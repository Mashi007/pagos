from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.asesor import Asesor
from app.models.user import User
from app.schemas.asesor import (
    AsesorCreate, 
    AsesorUpdate, 
    AsesorResponse,
    AsesorListResponse
)
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=AsesorListResponse)
def listar_asesores(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a retornar"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    👥 Listar todos los asesores con paginación y filtros
    """
    try:
        query = db.query(Asesor)
        
        # Aplicar filtros
        if activo is not None:
            query = query.filter(Asesor.activo == activo)
        
        if search:
            query = query.filter(
                Asesor.nombre.ilike(f"%{search}%") | 
                Asesor.apellido.ilike(f"%{search}%")
            )
        
        
        # Obtener total
        total = query.count()
        
        # Aplicar paginación
        asesores = query.offset(skip).limit(limit).all()
        
        # Calcular páginas
        pages = (total + limit - 1) // limit
        
        return AsesorListResponse(
            items=[AsesorResponse.model_validate(a) for a in asesores],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar asesores: {str(e)}")

@router.get("/test-simple")
def test_simple():
    """
    🧪 Endpoint simple sin base de datos
    """
    return {"mensaje": "Router de asesores funcionando", "status": "ok", "timestamp": "2025-10-15"}

@router.get("/test-activos")
def test_asesores_activos():
    """
    🧪 Endpoint de prueba para diagnosticar problemas
    """
    return {"mensaje": "Endpoint de asesores funcionando", "status": "ok"}

@router.get("/activos")
def listar_asesores_activos(
    db: Session = Depends(get_db)
):
    """
    👨‍💼 Listar solo asesores activos (para formularios)
    
    Simplificado: Sin filtros adicionales, solo asesores activos
    """
    try:
        query = db.query(Asesor).filter(Asesor.activo == True)
        asesores = query.all()
        return [a.to_dict() for a in asesores]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar asesores activos: {str(e)}")

@router.get("/{asesor_id}", response_model=AsesorResponse)
def obtener_asesor(
    asesor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Obtener un asesor por ID
    """
    asesor = db.query(Asesor).filter(Asesor.id == asesor_id).first()
    
    if not asesor:
        raise HTTPException(status_code=404, detail="Asesor no encontrado")
    
    return AsesorResponse.model_validate(asesor)

@router.post("", response_model=AsesorResponse)
def crear_asesor(
    asesor_data: AsesorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ➕ Crear un nuevo asesor
    """
    try:
        # Generar email automático si no se proporciona
        if not asesor_data.email:
            asesor_data.email = f"{asesor_data.nombre.lower().replace(' ', '.')}@asesor.local"
        
        # Verificar que no exista un asesor con el mismo email (solo si se proporciona email)
        if asesor_data.email:
            existing = db.query(Asesor).filter(Asesor.email == asesor_data.email).first()
            if existing:
                raise HTTPException(status_code=400, detail="Ya existe un asesor con este email")
        
        # Generar nombre_completo
        nombre_completo = asesor_data.nombre
        if asesor_data.apellido:
            nombre_completo = f"{asesor_data.nombre} {asesor_data.apellido}"
        
        # Crear nuevo asesor
        asesor_dict = asesor_data.dict()
        asesor_dict['nombre_completo'] = nombre_completo
        
        asesor = Asesor(**asesor_dict)
        db.add(asesor)
        db.commit()
        db.refresh(asesor)
        
        return AsesorResponse.model_validate(asesor)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear asesor: {str(e)}")

@router.put("/{asesor_id}", response_model=AsesorResponse)
def actualizar_asesor(
    asesor_id: int,
    asesor_data: AsesorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ✏️ Actualizar un asesor existente
    """
    try:
        asesor = db.query(Asesor).filter(Asesor.id == asesor_id).first()
        
        if not asesor:
            raise HTTPException(status_code=404, detail="Asesor no encontrado")
        
        # Verificar email único si se está cambiando
        if asesor_data.email and asesor_data.email != asesor.email:
            existing = db.query(Asesor).filter(
                Asesor.email == asesor_data.email,
                Asesor.id != asesor_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Ya existe un asesor con este email")
        
        # Actualizar campos
        update_data = asesor_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(asesor, field, value)
        
        db.commit()
        db.refresh(asesor)
        
        return AsesorResponse.model_validate(asesor)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar asesor: {str(e)}")

@router.delete("/{asesor_id}")
def eliminar_asesor(
    asesor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🗑️ Eliminar un asesor (soft delete - marcar como inactivo)
    """
    try:
        asesor = db.query(Asesor).filter(Asesor.id == asesor_id).first()
        
        if not asesor:
            raise HTTPException(status_code=404, detail="Asesor no encontrado")
        
        # Soft delete - marcar como inactivo
        asesor.activo = False
        db.commit()
        
        return {"message": "Asesor eliminado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar asesor: {str(e)}")
