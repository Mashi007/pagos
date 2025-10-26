"""
Servicio de autenticación
"""

import logging
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse

logger = logging.getLogger(__name__)


class AuthService:
    """Servicio de autenticación"""

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        Autentica un usuario con email y contraseña

        Args:
            db: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano

        Returns:
            User: Usuario autenticado o None si falla
        """
        # Consulta específica solo con columnas necesarias para autenticación
        # CASE INSENSITIVE: Normalizar email a minúsculas para búsqueda
        email_normalized = email.lower().strip()

        logger.info(f"Intentando autenticar usuario: {email_normalized}")

        user = db.query(User).filter(func.lower(User.email) == email_normalized, User.is_active).first()

        if not user:
            logger.warning(f"Usuario no encontrado o inactivo: {email_normalized}")
            return None

        if not verify_password(password, str(user.hashed_password)):
            logger.warning(f"Contraseña incorrecta para usuario: {email_normalized}")
            return None

        logger.info(f"Usuario autenticado exitosamente: {email_normalized}")
        return user

    @staticmethod
    def login(db: Session, login_data: LoginRequest) -> Tuple[TokenResponse, User]:
        """
        Realiza el login de un usuario

        Args:
            db: Sesión de base de datos
            login_data: Datos de login

        Returns:
            Tuple[TokenResponse, User]: Token y usuario autenticado

        Raises:
            ValueError: Si las credenciales son inválidas
        """
        user = AuthService.authenticate_user(db, login_data.email, login_data.password)

        if not user:
            raise ValueError("Credenciales inválidas")

        # Crear tokens
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800,  # 30 minutos
        )

        logger.info(f"Login exitoso para usuario: {user.email}")
        return token_response, user

    @staticmethod
    def refresh_token(db: Session, refresh_token: str) -> TokenResponse:
        """
        Renueva un token de acceso usando un refresh token

        Args:
            db: Sesión de base de datos
            refresh_token: Token de refresh

        Returns:
            TokenResponse: Nuevo token de acceso

        Raises:
            ValueError: Si el refresh token es inválido
        """
        from app.core.security import decode_token, get_token_subject

        try:
            # Decodificar el refresh token
            payload = decode_token(refresh_token)

            # Verificar que sea un refresh token
            if payload.get("type") != "refresh":
                raise ValueError("Token inválido: no es un refresh token")

            # Obtener el ID del usuario
            user_id = get_token_subject(refresh_token)
            if not user_id:
                raise ValueError("Token inválido: no se puede obtener el usuario")

            # Verificar que el usuario existe y está activo
            user = db.query(User).filter(User.id == int(user_id), User.is_active).first()

            if not user:
                raise ValueError("Usuario no encontrado o inactivo")

            # Crear nuevo token de acceso
            new_access_token = create_access_token(subject=str(user.id))
            new_refresh_token = create_refresh_token(subject=str(user.id))

            token_response = TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=1800,
            )

            logger.info(f"Token renovado exitosamente para usuario: {user.email}")
            return token_response

        except Exception as e:
            logger.error(f"Error renovando token: {str(e)}")
            raise ValueError("Token de refresh inválido")

    @staticmethod
    def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Cambia la contraseña de un usuario

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            current_password: Contraseña actual
            new_password: Nueva contraseña

        Returns:
            bool: True si el cambio fue exitoso

        Raises:
            ValueError: Si la contraseña actual es incorrecta
        """
        from app.core.security import get_password_hash

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Usuario no encontrado")

        # Verificar contraseña actual
        if not verify_password(current_password, str(user.hashed_password)):
            raise ValueError("Contraseña actual incorrecta")

        # Actualizar contraseña
        user.hashed_password = get_password_hash(new_password)
        db.commit()

        logger.info(f"Contraseña cambiada exitosamente para usuario: {user.email}")
        return True

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """
        Obtiene un usuario por su ID

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            User: Usuario encontrado o None
        """
        return db.query(User).filter(User.id == user_id, User.is_active).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        Obtiene un usuario por su email

        Args:
            db: Sesión de base de datos
            email: Email del usuario

        Returns:
            User: Usuario encontrado o None
        """
        email_normalized = email.lower().strip()
        return db.query(User).filter(func.lower(User.email) == email_normalized, User.is_active).first()
