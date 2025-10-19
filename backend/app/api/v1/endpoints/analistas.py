"""
Endpoints de gestión de analistas
CRUD completo para analistas
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from datetime import datetime
from app.db.session import get_db
from app.models.analista import Analista
from app.models.user import User
from app.schemas.analista import (
    AnalistaCreate, 
    AnalistaUpdate, 
    AnalistaResponse,
    AnalistaListResponse
)
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/test-no-auth")
def test_analistas_no_auth(
    db: Session = Depends(get_db)
):
    """
    Test endpoint sin autenticación para verificar analistas
    """
    try:
        total_analistas = db.query(Analista).count()
        analistas = db.query(Analista).limit(5).all()
        
        analistas_data = []
        for analista in analistas:
            analistas_data.append({
                "id": analista.id,
                "nombre": analista.nombre,
                "primer_nombre": analista.primer_nombre,
                "apellido": analista.apellido,
                "activo": analista.activo,
                "created_at": analista.created_at.isoformat() if analista.created_at else None
            })
        
        return {
            "success": True,
            "total_analistas": total_analistas,
            "analistas": analistas_data,
            "message": "Test endpoint analistas sin auth funcionando"
        }
    except Exception as e:
        logger.error(f"Error en test endpoint analistas no auth: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Error en test endpoint analistas no auth"
        }

@router.get("/health")
def health_check_analistas(db: Session = Depends(get_db)):
    """
    Health check específico para el módulo de analistas
    """
    try:
        # Verificar conexión a base de datos
        result = db.execute(text("SELECT COUNT(*) FROM analistas"))
        total = result.fetchone()[0]
        
        return {
            "status": "healthy",
            "module": "analistas",
            "total_records": total,
            "timestamp": datetime.now().isoformat(),
            "message": "Módulo de analistas funcionando correctamente"
        }
    except Exception as e:
        logger.error(f"Error en health check de analistas: {str(e)}")
        return {
            "status": "unhealthy",
            "module": "analistas",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "message": "Error en módulo de analistas"
        }

@router.get("/emergency")
def analistas_emergency(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a retornar"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db)
):
    """
    Endpoint de emergencia para analistas SIN autenticación
    Usar solo cuando el endpoint principal falle
    """
    try:
        # Usar SQL directo para máxima compatibilidad
        base_query = "SELECT id, nombre, activo, created_at FROM analistas"
        count_query = "SELECT COUNT(*) FROM analistas"
        where_conditions = []
        
        # Aplicar filtros
        if activo is not None:
            where_conditions.append(f"activo = {activo}")
        
        if search:
            where_conditions.append(f"nombre ILIKE '%{search}%'")
        
        # Agregar WHERE si hay condiciones
        if where_conditions:
            where_clause = " WHERE " + " AND ".join(where_conditions)
            base_query += where_clause
            count_query += where_clause
        
        # Obtener total
        total_result = db.execute(text(count_query))
        total = total_result.fetchone()[0]
        
        # Aplicar paginación
        paginated_query = f"{base_query} ORDER BY id OFFSET {skip} LIMIT {limit}"
        result = db.execute(text(paginated_query))
        rows = result.fetchall()
        
        # Calcular páginas
        pages = (total + limit - 1) // limit
        
        # Convertir filas a formato de respuesta
        items = []
        for row in rows:
            nombre_completo = row[1] if row[1] else ""
            partes_nombre = nombre_completo.split()
            primer_nombre = partes_nombre[0] if partes_nombre else ""
            apellido = " ".join(partes_nombre[1:]) if len(partes_nombre) > 1 else ""
            
            items.append({
                "id": row[0],
                "nombre": nombre_completo,
                "apellido": apellido,
                "email": "",
                "telefono": "",
                "especialidad": "",
                "comision_porcentaje": 0,
                "activo": row[2],
                "notas": "",
                "nombre_completo": nombre_completo,
                "primer_nombre": primer_nombre,
                "created_at": row[3].isoformat() if row[3] else None,
                "updated_at": None
            })
        
        return {
            "items": items,
            "total": total,
            "page": (skip // limit) + 1,
            "size": limit,
            "pages": pages,
            "emergency_mode": True,
            "message": "Endpoint de emergencia funcionando"
        }
        
    except Exception as e:
        logger.error(f"Error en endpoint de emergencia: {str(e)}")
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "size": limit,
            "pages": 0,
            "emergency_mode": True,
            "error": str(e),
            "message": "Error en endpoint de emergencia"
        }

@router.get("/list-no-auth")
def listar_analistas_no_auth(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a retornar"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db)
):
    """
    Listar analistas SIN autenticación (para testing)
    """
    try:
        query = db.query(Analista)
        
        # Aplicar filtros
        if activo is not None:
            query = query.filter(Analista.activo == activo)
        
        if search:
            query = query.filter(
                Analista.nombre.ilike(f"%{search}%") | 
                Analista.apellido.ilike(f"%{search}%")
            )
        
        # Obtener total
        total = query.count()
        
        # Aplicar paginación
        analistas = query.offset(skip).limit(limit).all()
        
        # Calcular páginas
        pages = (total + limit - 1) // limit
        
        return {
            "items": [AnalistaResponse.model_validate(a) for a in analistas],
            "total": total,
            "page": (skip // limit) + 1,
            "size": limit,
            "pages": pages
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar analistas: {str(e)}")

@router.get("/", response_model=AnalistaListResponse)
def listar_asesores(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a retornar"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar todos los asesores con paginación y filtros
    """
    try:
        # Construir consulta SQL base
        base_query = "SELECT id, nombre, activo, created_at FROM analistas"
        count_query = "SELECT COUNT(*) FROM analistas"
        where_conditions = []
        
        # Aplicar filtros
        if activo is not None:
            where_conditions.append(f"activo = {activo}")
        
        if search:
            where_conditions.append(f"nombre ILIKE '%{search}%'")
        
        # Agregar WHERE si hay condiciones
        if where_conditions:
            where_clause = " WHERE " + " AND ".join(where_conditions)
            base_query += where_clause
            count_query += where_clause
        
        # Obtener total
        total_result = db.execute(count_query)
        total = total_result.fetchone()[0]
        
        # Aplicar paginación
        paginated_query = f"{base_query} ORDER BY id OFFSET {skip} LIMIT {limit}"
        result = db.execute(paginated_query)
        rows = result.fetchall()
        
        # Calcular páginas
        pages = (total + limit - 1) // limit
        
        # Convertir filas a objetos AnalistaResponse
        items = []
        for row in rows:
            analista_data = {
                "id": row[0],
                "nombre": row[1],
                "apellido": " ".join(row[1].split()[1:]) if row[1] and len(row[1].split()) > 1 else "",
                "email": "",
                "telefono": "",
                "especialidad": "",
                "comision_porcentaje": 0,
                "activo": row[2],
                "notas": "",
                "nombre_completo": row[1],
                "primer_nombre": row[1].split()[0] if row[1] else "",
                "created_at": row[3],
                "updated_at": None
            }
            items.append(AnalistaResponse.model_validate(analista_data))
        
        return AnalistaListResponse(
            items=items,
            total=total,
            page=(skip // limit) + 1,
            size=limit,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar asesores: {str(e)}")

@router.get("/test-activos")
def test_asesores_activos():
    """
    Endpoint de prueba para diagnosticar problemas
    """
    return {"mensaje": "Endpoint de asesores funcionando", "status": "ok"}

@router.get("/activos")
def listar_asesores_activos(
    db: Session = Depends(get_db)
):
    """
    Listar solo asesores activos (para formularios)
    
    Simplificado: Sin filtros adicionales, solo asesores activos
    """
    try:
        query = db.query(Analista).filter(Analista.activo == True)
        asesores = query.all()
        return [AnalistaResponse.model_validate(a) for a in asesores]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar asesores activos: {str(e)}")

@router.get("/{asesor_id}", response_model=AnalistaResponse)
def obtener_asesor(
    asesor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener un asesor por ID
    """
    asesor = db.query(Analista).filter(Analista.id == asesor_id).first()
    
    if not asesor:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    
    return AnalistaResponse.model_validate(asesor)

@router.post("/crear", response_model=AnalistaResponse)
def crear_asesor(
    asesor_data: AnalistaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crear un nuevo asesor
    """
    try:
        # Generar email automático si no se proporciona
        if not asesor_data.email:
            asesor_data.email = f"{asesor_data.nombre.lower().replace(' ', '.')}@asesor.local"
        
        # Verificar que no exista un asesor con el mismo email (solo si se proporciona email)
        if asesor_data.email:
            existing = db.query(Analista).filter(Analista.email == asesor_data.email).first()
            if existing:
                raise HTTPException(status_code=400, detail="Ya existe un asesor con este email")
        
        # Crear nuevo asesor (nombre_completo es una propiedad, no se asigna)
        asesor_dict = asesor_data.model_dump()  # Pydantic v2
        
        asesor = Analista(**asesor_dict)
        db.add(asesor)
        db.commit()
        db.refresh(asesor)
        
        return AnalistaResponse.model_validate(asesor)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear asesor: {str(e)}")

@router.put("/{asesor_id}", response_model=AnalistaResponse)
def actualizar_asesor(
    asesor_id: int,
    asesor_data: AnalistaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar un asesor existente
    """
    try:
        asesor = db.query(Analista).filter(Analista.id == asesor_id).first()
        
        if not asesor:
            raise HTTPException(status_code=404, detail="Analista no encontrado")
        
        # Verificar email único si se está cambiando
        if asesor_data.email and asesor_data.email != asesor.email:
            existing = db.query(Analista).filter(
                Analista.email == asesor_data.email,
                Analista.id != asesor_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Ya existe un asesor con este email")
        
        # Actualizar campos
        update_data = asesor_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(asesor, field, value)
        
        db.commit()
        db.refresh(asesor)
        
        return AnalistaResponse.model_validate(asesor)
        
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
    Eliminar un analista (HARD DELETE - borrado completo de BD)
    """
    try:
        asesor = db.query(Analista).filter(Analista.id == asesor_id).first()
        
        if not asesor:
            raise HTTPException(status_code=404, detail="Analista no encontrado")
        
        # HARD DELETE - eliminar completamente de la base de datos
        asesor_nombre = asesor.nombre_completo  # Guardar nombre para log
        db.delete(asesor)
        db.commit()
        
        return {"message": "Analista eliminado completamente de la base de datos"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar analista: {str(e)}")
