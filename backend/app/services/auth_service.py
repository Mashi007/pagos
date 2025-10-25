# backend/app/services/auth_service.py
"""
Servicio de autenticación
Lógica de negocio para login, logout, refresh tokens
"""
import logging
from datetime import datetime
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, Token

logger = logging.getLogger(__name__)


class AuthService:
    """Servicio de autenticación"""

    @staticmethod
    def authenticate_user(
        db: Session, email: str, password: str
    ) -> Optional[User]:
        """
        Autentica un usuario con email y contraseña

        Args:
            db: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano

        Returns:
            Usuario si la autenticación es exitosa, None si no
        """
        # Consulta específica solo con columnas necesarias para autenticación
        # CASE INSENSITIVE: Normalizar email a minúsculas para búsqueda
        email_normalized = email.lower().strip()

        logger.info(
            f"AuthService.authenticate_user - Intentando autenticar "
            f"usuario: {email_normalized}"
        )

        user = (
            db.query(User)
            .filter(func.lower(User.email) == email_normalized, User.is_active)
            .first()
        )

        if not user:
            logger.warning(
                f"AuthService.authenticate_user - Usuario"
                + f"no encontrado: \
                {email_normalized}"
            )
            return None

        if not verify_password(password, user.hashed_password):
            logger.warning(
                f"AuthService.authenticate_user - Contraseña incorrecta para: {email_normalized}"
            )
            return None

        logger.info(
            f"AuthService.authenticate_user - Autenticación exitosa para: {email_normalized}"
        )
        return user

    @staticmethod
    def login(db: Session, login_data: LoginRequest) -> Tuple[Token, User]:
        """
        Realiza el login de un usuario

        Args:
            db: Sesión de base de datos
            login_data: Datos de login (email, password)

        Returns:
            Tupla de (Token, User)

        Raises:
            HTTPException: Si las credenciales son inválidas o el usuario está inactivo
        """
        # Autenticar usuario
        logger.info(
            f"AuthService.login - Iniciando proceso de login para: {login_data.email}"
        )

        user = AuthService.authenticate_user(
            db, login_data.email, login_data.password
        )

        if not user:
            logger.warning(
                f"AuthService.login - Fallo en autenticación para: {login_data.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verificar que el usuario esté activo
        if not user.is_active:
            logger.warning(
                f"AuthService.login - Usuario inactivo: {login_data.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo. Contacte al administrador.",
            )

        # Actualizar last_login
        user.last_login = datetime.utcnow()
        db.commit()

        logger.info(
            f"AuthService.login - Login exitoso para: {login_data.email}"
        )

        # Crear tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={
                "is_admin": user.is_admin,  # Cambio clave: rol → is_admin
                "email": user.email,
            },
        )
        refresh_token = create_refresh_token(subject=user.id)

        token = Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

        return token, user

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Token:
        """
        Genera un nuevo access token usando un refresh token

        Args:
            db: Sesión de base de datos
            refresh_token: Refresh token válido

        Returns:
            Nuevo par de tokens

        Raises:
            HTTPException: Si el refresh token es inválido
        """
        try:
            payload = decode_token(refresh_token)

            # Verificar que sea un refresh token
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido",
                )

            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido",
                )

            # Buscar usuario
            user = db.query(User).filter(User.id == int(user_id)).first()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado",
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuario inactivo",
                )

            # Crear nuevos tokens
            new_access_token = create_access_token(
                subject=user.id,
                additional_claims={
                    "is_admin": user.is_admin,  # Cambio clave: rol → is_admin
                    "email": user.email,
                },
            )
            new_refresh_token = create_refresh_token(subject=user.id)

            return Token(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Error procesando token: {str(e)}",
            )

    @staticmethod
    def change_password(
        db: Session, user: User, current_password: str, new_password: str
    ) -> User:
        """
        Cambia la contraseña de un usuario

        Args:
            db: Sesión de base de datos
            user: Usuario actual
            current_password: Contraseña actual
            new_password: Nueva contraseña

        Returns:
            Usuario actualizado

        Raises:
            HTTPException: Si la contraseña actual es incorrecta o la nueva es débil
        """
        # Verificar contraseña actual
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña actual incorrecta",
            )

        # Validar fortaleza de nueva contraseña
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=message
            )

        # Actualizar contraseña
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def get_user_permissions(user: User) -> list[str]:
        """
        Obtiene los permisos de un usuario basado en su rol

        Args:
            user: Usuario

        Returns:
            Lista de permisos (strings)
        """
        try:
            # Usar is_admin directamente - evitar conflicto de nombres
            from app.core.permissions_simple import (
                get_user_permissions as get_permissions,
            )

            permissions = get_permissions(user.is_admin)
            permission_strings = [perm.value for perm in permissions]

            return permission_strings
        except Exception:
            # Si hay error, retornar permisos vacíos
            return []
