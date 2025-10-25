from app.core.security import decode_token
from datetime import date
# backend/app/services/auth_service.py
"""Servicio de autenticación

Lógica de negocio para login, logout, refresh tokens
"""

import logging
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import 
from app.models.user import User
from app.schemas.auth import LoginRequest, Token

logger = logging.getLogger(__name__)


# Servicio de autenticación principal - Versión corregida


class AuthService:
    """Servicio de autenticación"""

    @staticmethod
    def authenticate_user
    ) -> Optional[User]:
        """
        Autentica un usuario con email y contraseña

        Args:
            email: Email del usuario
            password: Contraseña en texto plano

        Returns:
        """
        # Consulta específica solo con columnas necesarias para autenticación
        # CASE INSENSITIVE: Normalizar email a minúsculas para búsqueda
        email_normalized = email.lower().strip()

        logger.info

        user = 
            db.query(User)
            .filter(func.lower(User.email) == email_normalized, User.is_active)
            .first()

        if not user:
            logger.warning
            return None

        if not verify_password(password, user.hashed_password):
            logger.warning
            return None

        logger.info
        return user

    @staticmethod
    def login(db: Session, login_data: LoginRequest) -> Tuple[Token, User]:
        """
        Realiza el login de un usuario

        Args:

        Returns:
            Tupla de (Token, User)

        Raises:
            HTTPException: Si las credenciales son inválidas o el usuario está inactivo
        """
        # Autenticar usuario
        logger.info

        user = AuthService.authenticate_user

        if not user:
            logger.warning
            raise HTTPException

        # Verificar que el usuario esté activo
        if not user.is_active:
            logger.warning
            raise HTTPException

        # Actualizar last_login
        db.commit()

        logger.info

        # Crear tokens
        access_token = create_access_token
        refresh_token = create_refresh_token(subject=user.id)

        token = Token

        return token, user

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Token:
        """
        Genera un nuevo access token usando un refresh token

        Args:
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
                raise HTTPException

            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException

            # Buscar usuario
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                raise HTTPException

            if not user.is_active:
                raise HTTPException

            new_access_token = create_access_token
            new_refresh_token = create_refresh_token(subject=user.id)

            return Token

        except Exception as e:
            raise HTTPException
                detail=f"Error procesando token: {str(e)}",

    @staticmethod
    def change_password
    ) -> User:
        """
        Cambia la contraseña de un usuario

        Args:
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
            raise HTTPException

        # Validar fortaleza de nueva contraseña
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException

        # Actualizar contraseña
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def get_user_permissions(user: User) -> list[str]:
        """

        Args:
            user: Usuario

        Returns:
        """
        try:
            # Usar is_admin directamente - evitar conflicto de nombres
            from app.core.permissions_simple import 

            permissions = get_permissions(user.is_admin)
            permission_strings = [perm.value for perm in permissions]
            return permission_strings

        except Exception:
            return []

"""
"""