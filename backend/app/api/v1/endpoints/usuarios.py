"""
Endpoints de usuarios. CRUD contra tabla usuarios.
Solo administradores (rol=admin) pueden crear, actualizar, eliminar usuarios.
GET /api/v1/usuarios/ (listado), POST (crear), GET /{id}, PUT /{id}, DELETE /{id},
POST /{id}/activate, POST /{id}/deactivate, GET /verificar-admin.
POST /bulk (carga masiva de usuarios).
GET /kpis (estadísticas y KPIs de usuarios).
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.security import get_password_hash
from app.core.user_utils import user_to_response
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.usuario import UserCreate, UserUpdate
from app.schemas.usuario_bulk import UserBulkImportRequest, UserBulkImportResponse
from app.schemas.usuario_kpis import KpiUsuariosResponse
from app.services.usuario_bulk_import import procesar_importacion_usuarios

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=dict)
def listar_usuarios(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=2000),
    is_active: Optional[bool] = Query(None),
):
    """Listado de usuarios desde la tabla usuarios. Paginado y filtro is_active."""
    q = db.query(User)
    if is_active is not None:
        q = q.filter(User.is_active == is_active)
    total = q.count()
    offset = (page - 1) * page_size
    rows = q.order_by(User.id).offset(offset).limit(page_size).all()
    items = [user_to_response(u) for u in rows]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/verificar-admin", response_model=dict)
def verificar_admin(db: Session = Depends(get_db)):
    """Indica si existe al menos un usuario admin activo (para mostrar avisos en frontend)."""
    tiene = (
        db.query(User)
        .filter(User.rol == "admin", User.is_active == True)
        .limit(1)
        .first()
        is not None
    )
    return {"tiene_admin": tiene}


@router.get("/{user_id}", response_model=UserResponse)
def obtener_usuario(user_id: int, db: Session = Depends(get_db)):
    """Obtiene un usuario por ID."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user_to_response(u)


@router.post("", response_model=UserResponse)
def crear_usuario(
    body: UserCreate,
    admin: UserResponse = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Crea un nuevo usuario. Solo administradores. Email y cédula deben ser únicos."""
    email = body.email.lower().strip()
    cedula = body.cedula.strip()
    
    # Validar email único
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese email",
        )
    
    # Validar cédula única
    if db.query(User).filter(User.cedula == cedula).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con esa cédula",
        )
    
    now = datetime.utcnow()
    u = User(
        email=email,
        cedula=cedula,
        password_hash=get_password_hash(body.password),
        nombre=body.nombre.strip(),
        cargo=body.cargo.strip() if body.cargo else None,
        rol=body.rol,
        is_active=body.is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return user_to_response(u)


@router.put("/{user_id}", response_model=UserResponse)
def actualizar_usuario(
    user_id: int,
    body: UserUpdate,
    admin: UserResponse = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Actualiza un usuario. Solo administradores. Email y cédula deben ser únicos."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if body.email is not None:
        email = body.email.lower().strip()
        other = db.query(User).filter(User.email == email, User.id != user_id).first()
        if other:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro usuario con ese email",
            )
        u.email = email
    
    if body.cedula is not None:
        cedula = body.cedula.strip()
        other = db.query(User).filter(User.cedula == cedula, User.id != user_id).first()
        if other:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro usuario con esa cédula",
            )
        u.cedula = cedula
    
    if body.nombre is not None:
        u.nombre = body.nombre.strip()
    if body.cargo is not None:
        u.cargo = body.cargo.strip() if body.cargo else None
    if body.rol is not None:
        u.rol = body.rol
    if body.is_active is not None:
        u.is_active = body.is_active
    if body.password is not None and body.password.strip():
        u.password_hash = get_password_hash(body.password)

    u.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(u)
    return user_to_response(u)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(
    user_id: int,
    admin: UserResponse = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Desactiva el usuario (soft delete). Solo administradores. No borra el registro."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    u.is_active = False
    u.updated_at = datetime.utcnow()
    db.commit()
    return None


@router.post("/{user_id}/activate", response_model=UserResponse)
def activar_usuario(
    user_id: int,
    admin: UserResponse = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activa un usuario (is_active=True). Solo administradores."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    u.is_active = True
    u.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(u)
    return user_to_response(u)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def desactivar_usuario(
    user_id: int,
    admin: UserResponse = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Desactiva un usuario (is_active=False). Solo administradores."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    u.is_active = False
    u.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(u)
    return user_to_response(u)


@router.post("/bulk", response_model=UserBulkImportResponse)
def importar_usuarios_masivo(
    request: UserBulkImportRequest,
    admin: UserResponse = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Importación masiva de usuarios. Solo administradores.
    
    Máximo 1000 usuarios por solicitud.
    
    Validaciones:
    - Email debe ser único
    - Cédula debe ser única
    - Roles válidos: admin, manager, operator, viewer
    - Password mínimo 6 caracteres
    
    Respuesta:
    - Devuelve resultado de cada usuario (éxito o error)
    - Los usuarios exitosos se crean en la BD
    - Los usuarios con error no se crean
    """
    total_solicitados = len(request.usuarios)
    total_exitosos, total_errores, resultados = procesar_importacion_usuarios(
        db=db,
        usuarios=request.usuarios,
        admin_email=admin.email
    )
    
    return UserBulkImportResponse(
        total_solicitados=total_solicitados,
        total_exitosos=total_exitosos,
        total_errores=total_errores,
        resultados=resultados,
    )


@router.get("/kpis", response_model=KpiUsuariosResponse)
def obtener_kpis_usuarios(
    db: Session = Depends(get_db),
):
    """Obtiene KPIs y estadísticas de usuarios del sistema."""
    
    # Total de usuarios
    total_usuarios = db.query(func.count(User.id)).scalar() or 0
    
    # Usuarios activos
    usuarios_activos = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    
    # Usuarios inactivos
    usuarios_inactivos = db.query(func.count(User.id)).filter(User.is_active == False).scalar() or 0
    
    # Administradores activos
    admins_activos = db.query(func.count(User.id)).filter(
        User.rol == "admin",
        User.is_active == True
    ).scalar() or 0
    
    # Managers activos
    managers_activos = db.query(func.count(User.id)).filter(
        User.rol == "manager",
        User.is_active == True
    ).scalar() or 0
    
    # Operators activos
    operators_activos = db.query(func.count(User.id)).filter(
        User.rol == "operator",
        User.is_active == True
    ).scalar() or 0
    
    # Viewers activos
    viewers_activos = db.query(func.count(User.id)).filter(
        User.rol == "viewer",
        User.is_active == True
    ).scalar() or 0
    
    # Usuarios agregados en el último mes
    hace_un_mes = datetime.utcnow() - timedelta(days=30)
    usuarios_ultimo_mes = db.query(func.count(User.id)).filter(
        User.created_at >= hace_un_mes
    ).scalar() or 0
    
    # Usuarios agregados en últimos 7 días
    hace_una_semana = datetime.utcnow() - timedelta(days=7)
    usuarios_ultima_semana = db.query(func.count(User.id)).filter(
        User.created_at >= hace_una_semana
    ).scalar() or 0
    
    # Porcentaje de activos
    porcentaje_activos = round((usuarios_activos / total_usuarios * 100) if total_usuarios > 0 else 0, 1)
    
    # Último usuario creado
    ultimo_usuario = db.query(User).order_by(User.created_at.desc()).first()
    
    # Último login
    ultimo_login = db.query(User).filter(User.last_login != None).order_by(User.last_login.desc()).first()
    
    return KpiUsuariosResponse(
        total_usuarios=total_usuarios,
        usuarios_activos=usuarios_activos,
        usuarios_inactivos=usuarios_inactivos,
        porcentaje_activos=porcentaje_activos,
        por_rol={
            "admin": admins_activos,
            "manager": managers_activos,
            "operator": operators_activos,
            "viewer": viewers_activos,
        },
        usuarios_ultimo_mes=usuarios_ultimo_mes,
        usuarios_ultima_semana=usuarios_ultima_semana,
        ultimo_usuario_creado={
            "email": ultimo_usuario.email if ultimo_usuario else None,
            "fecha": ultimo_usuario.created_at.isoformat() if ultimo_usuario else None,
        },
        ultimo_login={
            "email": ultimo_login.email if ultimo_login else None,
            "fecha": ultimo_login.last_login.isoformat() if ultimo_login else None,
        },
    )
