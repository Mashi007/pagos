"""
Módulo de Seguridad - CSRF Token Management y Secure Cookies Configuration
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, status
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class CSRFToken(Base):
    """Modelo de base de datos para almacenar tokens CSRF"""
    __tablename__ = "csrf_tokens"
    
    session_id = Column(String(255), primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    def is_expired(self) -> bool:
        """Verificar si el token ha expirado"""
        return datetime.utcnow() > self.expires_at


class CSRFTokenManager:
    """
    Gestor de tokens CSRF para protección contra ataques Cross-Site Request Forgery.
    
    Genera, almacena y valida tokens únicos por sesión.
    Los tokens se invalidaban después de usarse una sola vez (one-time use).
    """
    
    TOKEN_LENGTH = 32  # 256 bits en base64url
    TOKEN_EXPIRY_MINUTES = 60  # Los tokens expiran en 1 hora
    
    def __init__(self, db_session=None):
        """
        Inicializar el gestor.
        
        Args:
            db_session: Sesión de SQLAlchemy para persistencia en BD
                       Si es None, usa almacenamiento en memoria (dev only)
        """
        self.db = db_session
        self._memory_tokens: Dict[str, Dict] = {}  # Fallback para dev
    
    def generate_token(self, session_id: str) -> str:
        """
        Generar un nuevo token CSRF único para una sesión.
        
        Args:
            session_id: ID única de la sesión del usuario
            
        Returns:
            Token CSRF en formato seguro (URL-safe)
        """
        # Generar token criptográficamente seguro
        token = secrets.token_urlsafe(self.TOKEN_LENGTH)
        expiry = datetime.utcnow() + timedelta(minutes=self.TOKEN_EXPIRY_MINUTES)
        
        if self.db:
            # Persistir en base de datos
            csrf_record = CSRFToken(
                session_id=session_id,
                token=token,
                expires_at=expiry
            )
            self.db.add(csrf_record)
            self.db.commit()
        else:
            # Fallback a memoria (desarrollo)
            self._memory_tokens[session_id] = {
                "token": token,
                "expires_at": expiry
            }
        
        return token
    
    def verify_token(self, session_id: str, token: str) -> bool:
        """
        Verificar que un token CSRF sea válido para la sesión dada.
        
        Args:
            session_id: ID de la sesión del usuario
            token: Token a validar
            
        Returns:
            True si el token es válido y coincide con la sesión
            
        Raises:
            HTTPException: Si el token es inválido, expirado o no pertenece a la sesión
        """
        try:
            if self.db:
                # Buscar en base de datos
                csrf_record = self.db.query(CSRFToken).filter(
                    CSRFToken.session_id == session_id,
                    CSRFToken.token == token
                ).first()
                
                if not csrf_record:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="CSRF token inválido o no encontrado"
                    )
                
                # Verificar que no haya expirado
                if csrf_record.is_expired():
                    self.db.delete(csrf_record)
                    self.db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="CSRF token expirado"
                    )
                
                # Token válido: eliminarlo (one-time use)
                self.db.delete(csrf_record)
                self.db.commit()
                return True
                
            else:
                # Fallback a memoria
                stored = self._memory_tokens.get(session_id)
                if not stored:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="CSRF token no encontrado"
                    )
                
                if stored["token"] != token:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="CSRF token inválido"
                    )
                
                if datetime.utcnow() > stored["expires_at"]:
                    del self._memory_tokens[session_id]
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="CSRF token expirado"
                    )
                
                # Token válido: eliminarlo
                del self._memory_tokens[session_id]
                return True
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al validar CSRF token: {str(e)}"
            )
    
    def cleanup_expired_tokens(self):
        """Limpiar tokens expirados de la base de datos (ejecutar periódicamente)"""
        if self.db:
            self.db.query(CSRFToken).filter(
                CSRFToken.expires_at < datetime.utcnow()
            ).delete()
            self.db.commit()


class SecureCookieConfig:
    """
    Configuración de cookies seguras para proteger sesiones.
    
    Implementa los flags recomendados por OWASP:
    - httpOnly: Previene acceso desde JavaScript (XSS)
    - secure: Solo se envía por HTTPS
    - samesite: Previene CSRF (strict | lax | none)
    """
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        
        # Nombres de cookies
        self.SESSION_COOKIE_NAME = "rapicredit_session"
        self.REFRESH_COOKIE_NAME = "rapicredit_refresh"
        
        # Duración
        self.SESSION_COOKIE_MAX_AGE = 3600  # 1 hora
        self.REFRESH_COOKIE_MAX_AGE = 604800  # 7 días
        
        # Flags de seguridad
        self.COOKIE_SECURE = environment == "production"  # True en prod, False en dev
        self.COOKIE_HTTPONLY = True  # Siempre True
        self.COOKIE_SAMESITE = "strict"  # strict | lax | none
        
    def get_session_cookie_kwargs(self) -> dict:
        """Obtener kwargs para set_cookie() de sesión"""
        return {
            "key": self.SESSION_COOKIE_NAME,
            "httponly": self.COOKIE_HTTPONLY,
            "secure": self.COOKIE_SECURE,
            "samesite": self.COOKIE_SAMESITE,
            "max_age": self.SESSION_COOKIE_MAX_AGE,
            "path": "/",
        }
    
    def get_refresh_cookie_kwargs(self) -> dict:
        """Obtener kwargs para set_cookie() de refresh token"""
        return {
            "key": self.REFRESH_COOKIE_NAME,
            "httponly": self.COOKIE_HTTPONLY,
            "secure": self.COOKIE_SECURE,
            "samesite": self.COOKIE_SAMESITE,
            "max_age": self.REFRESH_COOKIE_MAX_AGE,
            "path": "/",
        }
    
    def get_delete_cookie_kwargs(self, cookie_name: str) -> dict:
        """Obtener kwargs para delete_cookie()"""
        return {
            "key": cookie_name,
            "path": "/",
            "secure": self.COOKIE_SECURE,
            "httponly": self.COOKIE_HTTPONLY,
            "samesite": self.COOKIE_SAMESITE,
        }


# Instancia global para usar en toda la aplicación
csrf_manager = CSRFTokenManager()
secure_cookie_config = SecureCookieConfig(environment="production")
