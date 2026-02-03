"""
Endpoints de usuarios. CRUD contra tabla usuarios.
GET /api/v1/usuarios/ (listado), POST (crear), GET /{id}, PUT /{id}, DELETE /{id},
POST /{id}/activate, POST /{id}/deactivate, GET /verificar-admin.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import get_password_hash
from app.core.user_utils import user_to_response
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.usuario import UserCreate, UserUpdate

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
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
    """Indica si existe al menos un usuario administrador activo (para mostrar avisos en frontend)."""
    tiene = (
        db.query(User)
        .filter(User.rol == "administrador", User.is_active == True)
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


@router.post("/", response_model=UserResponse)
def crear_usuario(body: UserCreate, db: Session = Depends(get_db)):
    """Crea un nuevo usuario. Email debe ser único."""
    email = body.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese email",
        )
    now = datetime.utcnow()
    u = User(
        email=email,
        password_hash=get_password_hash(body.password),
        nombre=body.nombre.strip(),
        apellido=(body.apellido or "").strip(),
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
def actualizar_usuario(user_id: int, body: UserUpdate, db: Session = Depends(get_db)):
    """Actualiza un usuario. Si se envía password, se hashea y guarda."""
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
    if body.nombre is not None:
        u.nombre = body.nombre.strip()
    if body.apellido is not None:
        u.apellido = body.apellido.strip()
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
def eliminar_usuario(user_id: int, db: Session = Depends(get_db)):
    """Desactiva el usuario (soft delete). No borra el registro."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    u.is_active = False
    u.updated_at = datetime.utcnow()
    db.commit()
    return None


@router.post("/{user_id}/activate", response_model=UserResponse)
def activar_usuario(user_id: int, db: Session = Depends(get_db)):
    """Activa un usuario (is_active=True)."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    u.is_active = True
    u.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(u)
    return user_to_response(u)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def desactivar_usuario(user_id: int, db: Session = Depends(get_db)):
    """Desactiva un usuario (is_active=False)."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    u.is_active = False
    u.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(u)
    return user_to_response(u)
