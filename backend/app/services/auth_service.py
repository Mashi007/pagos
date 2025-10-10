# backend/app/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import UserCreate, Token
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type
)
from app.core.constants import EstadoUsuario


class AuthService:
    """Servicio de autenticación"""
    
    def __init__(self, db: Session, secret_key: str, algorithm: str):
        self.db = db
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Autenticar usuario con username y password
        
        Returns:
            User si las credenciales son correctas, None si no
        """
        user = self.db.query(User).filter(
            User.username == username.lower()
        ).first()
        
        if not user:
            return None
        
        # Verificar si está bloqueado
        if user.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Usuario bloqueado hasta {user.bloqueado_hasta}"
            )
        
        # Verificar contraseña
        if not verify_password(password, user.hashed_password):
            # Incrementar intentos fallidos
            user.intentos_fallidos += 1
            
            # Bloquear después de 5 intentos
            if user.intentos_fallidos >= 5:
                user.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=30)
                self.db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Demasiados intentos fallidos. Usuario bloqueado por 30 minutos"
                )
            
            self.db.commit()
            return None
        
        # Verificar estado
        if user.estado != EstadoUsuario.ACTIVO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Usuario {user.estado.value}"
            )
        
        # Login exitoso - resetear intentos
        user.intentos_fallidos = 0
        user.ultimo_login = datetime.utcnow()
        self.db.commit()
        
        return user
    
    def create_tokens(self, user_id: int) -> Token:
        """Crear access token y refresh token"""
        
        access_token = create_access_token(
            data={"sub": str(user_id)},
            secret_key=self.secret_key,
            algorithm=self.algorithm,
            expires_delta=timedelta(minutes=30)
        )
        
        refresh_token = create_refresh_token(
            data={"sub": str(user_id)},
            secret_key=self.secret_key,
            algorithm=self.algorithm,
            expires_delta=timedelta(days=7)
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token
        )
    
    def refresh_access_token(self, refresh_token: str) -> Token:
        """Refrescar access token usando refresh token"""
        
        # Decodificar refresh token
        payload = decode_token(refresh_token, self.secret_key, self.algorithm)
        
        # Verificar que sea refresh token
        verify_token_type(payload, "refresh")
        
        # Obtener user_id
        user_id = int(payload.get("sub"))
        
        # Verificar que el usuario existe y está activo
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.estado != EstadoUsuario.ACTIVO:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no válido"
            )
        
        # Crear nuevos tokens
        return self.create_tokens(user_id)
    
    def create_user(self, user_data: UserCreate, created_by: Optional[int] = None) -> User:
        """Crear nuevo usuario"""
        
        # Verificar que no exista el email
        existing_email = self.db.query(User).filter(
            User.email == user_data.email
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        
        # Verificar que no exista el username
        existing_username = self.db.query(User).filter(
            User.username == user_data.username.lower()
        ).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El username ya está registrado"
            )
        
        # Crear usuario
        db_user = User(
            email=user_data.email,
            username=user_data.username.lower(),
            nombre_completo=user_data.nombre_completo,
            telefono=user_data.telefono,
            rol=user_data.rol,
            hashed_password=get_password_hash(user_data.password),
            estado=EstadoUsuario.ACTIVO,
            debe_cambiar_password=True,
            creado_por=created_by
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> User:
        """Cambiar contraseña de usuario"""
        
        # Verificar contraseña actual
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña actual incorrecta"
            )
        
        # Actualizar contraseña
        user.hashed_password = get_password_hash(new_password)
        user.debe_cambiar_password = False
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def reset_password(self, user_id: int, new_password: str) -> User:
        """Resetear contraseña (solo admin)"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        user.hashed_password = get_password_hash(new_password)
        user.debe_cambiar_password = True
        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
