# backend/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.schemas.user import (
    LoginRequest,
    Token,
    RefreshTokenRequest,
    UserResponse,
    UserProfile
)
from app.services.auth_service import AuthService
from app.models.user import User
from app.config import settings


router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login con username y password
    
    Retorna access_token y refresh_token
    """
    auth_service = AuthService(db, settings.SECRET_KEY, settings.ALGORITHM)
    
    # Autenticar usuario
    user = auth_service.authenticate_user(
        login_data.username,
        login_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear tokens
    tokens = auth_service.create_tokens(user.id)
    
    return tokens


@router.post("/refresh", response_model=Token)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refrescar access token usando refresh token
    
    Retorna nuevo access_token y refresh_token
    """
    auth_service = AuthService(db, settings.SECRET_KEY, settings.ALGORITHM)
    
    tokens = auth_service.refresh_access_token(refresh_data.refresh_token)
    
    return tokens


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout (invalidar token en el cliente)
    
    Nota: JWT es stateless, el cliente debe eliminar el token
    """
    return {"message": "Logout exitoso"}


@router.get("/me", response_model=UserProfile)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Obtener perfil del usuario actual"""
    return current_user


@router.get("/verify")
def verify_token(current_user: User = Depends(get_current_user)):
    """
    Verificar si el token es válido
    
    Útil para el frontend para validar sesión
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "rol": current_user.rol
    }
