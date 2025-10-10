# backend/app/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.models.user import User
from app.schemas.auth import Token, LoginRequest
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Servicio de autenticación"""
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        Autenticar usuario por email y contraseña
        
        Args:
            db: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano
            
        Returns:
            Usuario si las credenciales son correctas, None si no
        """
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            logger.warning(f"Intento de login con email inexistente: {email}")
            return None
        
        if not user.activo:
            logger.warning(f"Intento de login de usuario inactivo: {email}")
            return None
        
        if not verify_password(password, user.password):
            logger.warning(f"Contraseña incorrecta para usuario: {email}")
            return None
        
        # Actualizar última conexión
        user.ultima_conexion = datetime.utcnow()
        db.commit()
        
        logger.info(f"Login exitoso: {email}")
        return user
    
    @staticmethod
    def login(db: Session, login_data: LoginRequest) -> Token:
        """
        Procesar login y generar tokens
        
        Args:
            db: Sesión de base de datos
            login_data: Datos de login
            
        Returns:
            Token JWT de acceso y refresh
            
        Raises:
            HTTPException: Si las credenciales son incorrectas
        """
        user = AuthService.authenticate_user(
            db, 
            login_data.email, 
            login_data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Crear tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.rol
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token({"sub": str(user.id)})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800  # 30 minutos
        )
    
    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Token:
        """
        Refrescar access token usando refresh token
        
        Args:
            db: Sesión de base de datos
            refresh_token: Refresh token válido
            
        Returns:
            Nuevo access token
            
        Raises:
            HTTPException: Si el token es inválido
        """
        payload = verify_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if not user or not user.activo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inválido o inactivo"
            )
        
        # Crear nuevo access token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.rol
        }
        
        new_access_token = create_access_token(token_data)
        
        return Token(
            access_token=new_access_token,
            refresh_token=refresh_token,  # Mantener el mismo refresh token
            token_type="bearer",
            expires_in=1800
        )
    
    @staticmethod
    def create_user(db: Session, email: str, password: str, nombre: str, 
                   apellido: str, rol: str) -> User:
        """
        Crear nuevo usuario
        
        Args:
            db: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano
            nombre: Nombre del usuario
            apellido: Apellido del usuario
            rol: Rol del usuario
            
        Returns:
            Usuario creado
            
        Raises:
            HTTPException: Si el email ya existe
        """
        # Verificar si el email ya existe
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        
        # Crear usuario
        hashed_password = get_password_hash(password)
        new_user = User(
            email=email,
            password=hashed_password,
            nombre=nombre,
            apellido=apellido,
            rol=rol,
            activo=True,
            fecha_creacion=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"Usuario creado: {email} ({rol})")
        return new_user
