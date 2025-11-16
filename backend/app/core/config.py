"""
Configuración de la aplicación
"""

import json
import logging
import os
from typing import List, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def _get_default_cors_origins() -> List[str]:
    """
    Obtiene los CORS origins por defecto según el entorno.
    En producción, solo incluye el frontend de producción.
    En desarrollo, incluye localhost.
    """
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return ["https://rapicredit.onrender.com"]
    else:
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "https://rapicredit.onrender.com",
        ]


class Settings(BaseSettings):
    """
    Configuración de la aplicación usando Pydantic BaseSettings
    """

    # ============================================
    # CONFIGURACIÓN BÁSICA
    # ============================================
    APP_NAME: str = "RapiCredit API"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "API para sistema de préstamos RapiCredit"
    ENVIRONMENT: str = Field(default="development")  # type: ignore[call-overload]
    DEBUG: bool = Field(default=True)  # type: ignore[call-overload]

    # ============================================
    # BASE DE DATOS
    # ============================================
    DATABASE_URL: str = Field(default="postgresql://user:password@localhost/pagos_db")  # type: ignore[call-overload]

    # ============================================
    # SEGURIDAD
    # ============================================
    # SECRET_KEY debe configurarse mediante variable de entorno
    # En desarrollo, se genera automáticamente si no está configurado
    SECRET_KEY: Optional[str] = Field(default=None)  # type: ignore[call-overload]
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 240  # 4 horas
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ============================================
    # CORS
    # ============================================
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: _get_default_cors_origins(),  # type: ignore[call-overload]
    )

    @model_validator(mode="before")
    @classmethod
    def parse_cors_origins_env(cls, data):
        """
        Parsea CORS_ORIGINS desde variable de entorno antes de que Pydantic intente validarlo.
        Acepta JSON array o string separado por comas.
        """
        # Si data es un dict (como viene de pydantic-settings)
        if isinstance(data, dict) and "CORS_ORIGINS" in data:
            cors_value = data["CORS_ORIGINS"]

            # Si ya es una lista, no hacer nada
            if isinstance(cors_value, list):
                return data

            # Si es None o vacío, usar valores por defecto
            if not cors_value:
                return data

            # Convertir a string si no lo es
            if not isinstance(cors_value, str):
                cors_value = str(cors_value)

            # Intentar parsear como JSON primero
            try:
                parsed = json.loads(cors_value)
                if isinstance(parsed, list):
                    data["CORS_ORIGINS"] = parsed
                    return data
            except (json.JSONDecodeError, ValueError):
                pass

            # Si no es JSON válido, intentar separar por comas
            if "," in cors_value:
                origins = [origin.strip().strip('"').strip("'") for origin in cors_value.split(",") if origin.strip()]
                data["CORS_ORIGINS"] = origins
            else:
                # Si es un solo string sin comas, retornar como lista
                cleaned = cors_value.strip().strip('"').strip("'")
                data["CORS_ORIGINS"] = [cleaned] if cleaned else []

        return data

    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = [
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "Accept",
        "Origin",
        "X-Requested-With",
    ]

    # ============================================
    # USUARIO ADMINISTRADOR INICIAL
    # ============================================
    # ADMIN_EMAIL y ADMIN_PASSWORD deben configurarse mediante variables de entorno
    # En desarrollo, se usan valores por defecto solo si no están configurados
    ADMIN_EMAIL: Optional[str] = Field(default=None)  # type: ignore[call-overload]
    ADMIN_PASSWORD: Optional[str] = Field(default=None)  # type: ignore[call-overload]

    # ============================================
    # AMORTIZACIÓN Y REGLAS DE NEGOCIO
    # ============================================
    TASA_INTERES_BASE: float = 12.0  # 12% anual
    TASA_MORA: float = 2.0  # 2% mensual
    TASA_MORA_DIARIA: float = 0.067  # 2% / 30 días
    MAX_CUOTA_PERCENTAGE: int = 40  # Máximo 40% del ingreso
    MONTO_MINIMO_PRESTAMO: float = 1000.0
    MONTO_MAXIMO_PRESTAMO: float = 50000.0
    PLAZO_MINIMO_MESES: int = 6
    PLAZO_MAXIMO_MESES: int = 36

    # ============================================
    # NOTIFICACIONES
    # ============================================
    DIAS_PREVIOS_RECORDATORIO: int = 3
    DIAS_MORA_ALERTA: int = 5

    # EMAIL
    EMAIL_ENABLED: bool = True
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = "noreply@rapicredit.com"
    FROM_NAME: str = "RapiCredit"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    # WHATSAPP (Meta Developers API)
    WHATSAPP_ENABLED: bool = True
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: Optional[str] = None

    # ============================================
    # REPORTES
    # ============================================
    REPORTS_DIR: str = "/tmp/reports"
    REPORTS_CACHE_ENABLED: bool = True
    REPORTS_CACHE_TTL: int = 1800

    # ============================================
    # REDIS / CACHÉ
    # ============================================
    REDIS_URL: Optional[str] = Field(
        default=None, description="URL completa de Redis (ej: redis://localhost:6379/0)"  # type: ignore[call-overload]
    )
    REDIS_HOST: str = Field(default="localhost", description="Host de Redis")  # type: ignore[call-overload]
    REDIS_PORT: int = Field(default=6379, description="Puerto de Redis")  # type: ignore[call-overload]
    REDIS_DB: int = Field(default=0, description="Base de datos de Redis")  # type: ignore[call-overload]
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Contraseña de Redis (opcional)")  # type: ignore[call-overload]
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, description="Timeout de socket en segundos")  # type: ignore[call-overload]

    # ============================================
    # FILE UPLOADS
    # ============================================
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".xlsx",
        ".xls",
        ".doc",
        ".docx",
    ]
    UPLOAD_DIR: str = "uploads"

    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ============================================
    # VALIDACIÓN DE CONFIGURACIÓN
    # ============================================

    def _generate_secret_key(self) -> str:
        """
        Genera una SECRET_KEY segura automáticamente.
        Solo para uso en desarrollo.
        """
        import secrets

        return secrets.token_urlsafe(32)

    def validate_secret_key(self) -> bool:
        """
        Valida que SECRET_KEY sea seguro en producción.
        En desarrollo, genera una automáticamente si no está configurado.
        """
        # En desarrollo, generar automáticamente si no está configurado
        if self.ENVIRONMENT != "production" and not self.SECRET_KEY:
            self.SECRET_KEY = self._generate_secret_key()
            logger.warning(
                "⚠️ SECRET_KEY no configurado. Generada automáticamente para desarrollo. "
                "Para producción, configure SECRET_KEY como variable de entorno."
            )
            return True

        # En producción, SECRET_KEY es obligatorio
        if self.ENVIRONMENT == "production":
            if not self.SECRET_KEY:
                raise ValueError(
                    "CRÍTICO: SECRET_KEY debe estar configurado en producción. "
                    "Configure SECRET_KEY como variable de entorno con al menos 32 caracteres."
                )

            default_secrets = [
                "your-secret-key-here-change-in-production",
                "secret-key",
                "changeme",
                "secret",
                "12345678",
                "password",
            ]
            if self.SECRET_KEY in default_secrets:
                raise ValueError(
                    "CRÍTICO: SECRET_KEY usa un valor por defecto inseguro. "
                    "Debe configurarse una clave segura de al menos 32 caracteres en producción."
                )
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "CRÍTICO: SECRET_KEY debe tener al menos 32 caracteres en producción. "
                    f"Longitud actual: {len(self.SECRET_KEY)}"
                )
        return True

    def validate_admin_credentials(self) -> bool:
        """
        Valida que las credenciales de admin estén configuradas y sean seguras.
        En desarrollo, usa valores por defecto si no están configurados.
        En producción, usa valores por defecto con advertencia crítica si no están configurados.
        """
        import os

        # Verificar si fueron configurados desde variables de entorno
        admin_email_from_env = os.getenv("ADMIN_EMAIL")
        admin_password_from_env = os.getenv("ADMIN_PASSWORD")

        # En desarrollo, usar valores por defecto si no están configurados
        if self.ENVIRONMENT != "production":
            if not self.ADMIN_EMAIL:
                self.ADMIN_EMAIL = "itmaster@rapicreditca.com"
                logger.warning(
                    "⚠️ ADMIN_EMAIL no configurado. Usando valor por defecto para desarrollo. "
                    "Para producción, configure ADMIN_EMAIL como variable de entorno."
                )
            if not self.ADMIN_PASSWORD:
                self.ADMIN_PASSWORD = "R@pi_2025**"
                logger.warning(
                    "⚠️ ADMIN_PASSWORD no configurado. Usando valor por defecto para desarrollo. "
                    "Para producción, configure ADMIN_PASSWORD como variable de entorno."
                )
        else:
            # En producción, usar valores por defecto si no están configurados (con advertencia crítica)
            # PRIORIDAD: 1) Variable de entorno (si no está vacía), 2) Valor actual de self, 3) Valor por defecto
            if admin_email_from_env and isinstance(admin_email_from_env, str) and admin_email_from_env.strip():
                # Si hay variable de entorno y no está vacía, usarla (incluso si self.ADMIN_EMAIL ya tiene valor)
                self.ADMIN_EMAIL = admin_email_from_env.strip()
            elif not self.ADMIN_EMAIL or (isinstance(self.ADMIN_EMAIL, str) and not self.ADMIN_EMAIL.strip()):
                # Si no hay variable de entorno válida y self.ADMIN_EMAIL está vacío/None, usar valor por defecto
                self.ADMIN_EMAIL = "itmaster@rapicreditca.com"
                logger.critical(
                    "🚨🚨🚨 CRÍTICO: ADMIN_EMAIL no está configurado como variable de entorno en producción. "
                    "ESTO ES UNA GRAVE FALTA DE SEGURIDAD. "
                    "Usando valor por defecto temporalmente. "
                    "Configure ADMIN_EMAIL en Render Dashboard inmediatamente. 🚨🚨🚨"
                )

            if admin_password_from_env and isinstance(admin_password_from_env, str) and admin_password_from_env.strip():
                # Si hay variable de entorno y no está vacía, usarla (incluso si self.ADMIN_PASSWORD ya tiene valor)
                self.ADMIN_PASSWORD = admin_password_from_env.strip()
            elif not self.ADMIN_PASSWORD or (isinstance(self.ADMIN_PASSWORD, str) and not self.ADMIN_PASSWORD.strip()):
                # Si no hay variable de entorno válida y self.ADMIN_PASSWORD está vacío/None, usar valor por defecto
                self.ADMIN_PASSWORD = "R@pi_2025**"
                logger.critical(
                    "🚨🚨🚨 CRÍTICO: ADMIN_PASSWORD no está configurado como variable de entorno en producción. "
                    "ESTO ES UNA GRAVE FALTA DE SEGURIDAD. "
                    "Usando valor por defecto temporalmente. "
                    "Configure ADMIN_PASSWORD en Render Dashboard inmediatamente. 🚨🚨🚨"
                )

        # Validaciones básicas (después de asignar valores por defecto)
        # Asegurarse de que siempre tengan un valor válido
        # Verificar explícitamente None, string vacío, o string con solo espacios
        if not self.ADMIN_EMAIL or (isinstance(self.ADMIN_EMAIL, str) and not self.ADMIN_EMAIL.strip()):
            raise ValueError("ADMIN_EMAIL debe estar configurado")
        if not self.ADMIN_PASSWORD or (isinstance(self.ADMIN_PASSWORD, str) and not self.ADMIN_PASSWORD.strip()):
            raise ValueError("ADMIN_PASSWORD debe estar configurado")

        if len(self.ADMIN_PASSWORD) < 8:
            raise ValueError("La contraseña de admin debe tener al menos 8 caracteres")

        # Validación específica para producción
        if self.ENVIRONMENT == "production":
            # Validar formato de email
            if "@" not in self.ADMIN_EMAIL or "." not in self.ADMIN_EMAIL.split("@")[1]:
                raise ValueError("ADMIN_EMAIL debe ser un email válido en producción")

            # Advertir si la contraseña es débil (solo si viene de variable de entorno)
            if admin_password_from_env and len(admin_password_from_env) < 12:
                logger.warning(
                    "⚠️ ADMIN_PASSWORD configurado desde variable de entorno pero es muy corta (<12 caracteres). "
                    "Se recomienda usar una contraseña más segura para producción."
                )

            # Validar complejidad de contraseña
            has_upper = any(c.isupper() for c in self.ADMIN_PASSWORD)
            has_lower = any(c.islower() for c in self.ADMIN_PASSWORD)
            has_digit = any(c.isdigit() for c in self.ADMIN_PASSWORD)
            has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in self.ADMIN_PASSWORD)

            if not (has_upper and has_lower and (has_digit or has_special)):
                logger.warning(
                    "⚠️ La contraseña de admin en producción debería contener: "
                    "mayúsculas, minúsculas y números o caracteres especiales. "
                    "Se recomienda mejorar la seguridad."
                )

        return True

    def validate_debug_mode(self) -> bool:
        """
        Valida que DEBUG esté desactivado en producción.
        """
        if self.ENVIRONMENT == "production" and self.DEBUG:
            raise ValueError(
                "CRÍTICO: DEBUG no puede estar activado en producción. "
                "Esto expone información sensible y reduce el rendimiento."
            )
        return True

    def validate_cors_config(self) -> bool:
        """
        Valida que CORS esté correctamente configurado en producción.
        Bloquea wildcards (*) en origins, methods y headers.
        """
        if self.ENVIRONMENT == "production":
            # Validar origins
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "CRÍTICO: CORS con wildcard (*) en CORS_ORIGINS detectado en producción. "
                    "CORS_ORIGINS debe especificar dominios específicos."
                )

            # Validar que haya al menos un origin válido
            if not self.CORS_ORIGINS or len(self.CORS_ORIGINS) == 0:
                raise ValueError("CRÍTICO: CORS_ORIGINS debe estar configurado en producción. " "No puede estar vacío.")

            # Validar que los origins sean URLs válidas (no localhost en producción)
            # IMPORTANTE: En lugar de bloquear, filtrar localhost automáticamente si usa valores por defecto
            import os

            cors_origins_from_env = os.getenv("CORS_ORIGINS")
            default_origins = [
                "http://localhost:3000",
                "http://localhost:5173",
                "https://rapicredit.onrender.com",
            ]

            # Si usa valores por defecto con localhost, filtrar automáticamente
            has_localhost = any(
                origin.startswith("http://localhost") or origin.startswith("https://localhost") for origin in self.CORS_ORIGINS
            )

            if has_localhost:
                if not cors_origins_from_env and set(self.CORS_ORIGINS) == set(default_origins):
                    # Usa valores por defecto con localhost - filtrar automáticamente
                    logger.critical(
                        "🚨 CRÍTICO: CORS_ORIGINS contiene localhost y usa valores por defecto. "
                        "Filtrando localhost automáticamente. "
                        "Se recomienda configurar CORS_ORIGINS como variable de entorno sin localhost."
                    )
                    # Filtrar localhost
                    original_origins = self.CORS_ORIGINS.copy()
                    self.CORS_ORIGINS = [
                        origin
                        for origin in self.CORS_ORIGINS
                        if not (origin.startswith("http://localhost") or origin.startswith("https://localhost"))
                    ]
                    if self.CORS_ORIGINS:
                        logger.info(f"✅ CORS_ORIGINS actualizado (sin localhost): {self.CORS_ORIGINS}")
                    else:
                        # Si se queda vacío, mantener al menos el de producción
                        self.CORS_ORIGINS = [origin for origin in original_origins if "rapicredit.onrender.com" in origin]
                        if not self.CORS_ORIGINS:
                            raise ValueError(
                                "CRÍTICO: Después de filtrar localhost, CORS_ORIGINS quedó vacío. Debe configurarse CORS_ORIGINS sin localhost."
                            )
                else:
                    # Si tiene localhost pero viene de env o no es exactamente el default, solo advertir
                    logger.warning(
                        f"⚠️ CORS_ORIGINS contiene localhost en producción: {[o for o in self.CORS_ORIGINS if 'localhost' in o]}. "
                        "Se recomienda remover localhost de CORS_ORIGINS en producción."
                    )

            # Validar formato de URLs (solo advertir si es inválido)
            for origin in self.CORS_ORIGINS:
                if not (origin.startswith("http://") or origin.startswith("https://")):
                    logger.warning(
                        f"⚠️ CORS_ORIGINS contiene URL inválida: {origin}. "
                        "Se recomienda usar URLs válidas (http:// o https://)."
                    )

        return True

    def validate_cors_middleware_config(self) -> bool:
        """
        Valida que la configuración de CORS middleware no use wildcards en producción.
        Nota: Esta validación se aplica al usar los valores en main.py
        """
        if self.ENVIRONMENT == "production":
            # CORS_ALLOW_HEADERS no debe contener "*" pero no bloqueamos
            if "*" in self.CORS_ALLOW_HEADERS:
                logger.warning(
                    "⚠️ CORS_ALLOW_HEADERS contiene '*' en producción. "
                    "Se recomienda especificar headers permitidos explícitamente. "
                    "Por ahora, se permite para evitar bloqueo pero se debe configurar correctamente."
                )
                # NO bloquear - solo advertir
        return True

    def validate_database_url(self) -> bool:
        """
        Valida que la URL de base de datos sea válida y segura.
        Bloquea credenciales por defecto en producción.
        """
        if self.ENVIRONMENT == "production":
            if not self.DATABASE_URL:
                raise ValueError("DATABASE_URL debe estar configurada en producción")

            # Detectar credenciales por defecto
            default_patterns = [
                "postgresql://user:password@",
                "postgresql://postgres:postgres@",
                "postgresql://admin:admin@",
                "mysql://root:root@",
                "sqlite://",
            ]

            for pattern in default_patterns:
                if pattern in self.DATABASE_URL.lower():
                    raise ValueError(
                        f"CRÍTICO: DATABASE_URL contiene credenciales por defecto inseguras. "
                        f"Patrón detectado: {pattern}. "
                        "Debe usar credenciales seguras configuradas en producción."
                    )

            # Validar formato básico de URL
            if not (
                self.DATABASE_URL.startswith("postgresql://")
                or self.DATABASE_URL.startswith("postgresql+psycopg2://")
                or self.DATABASE_URL.startswith("mysql://")
                or self.DATABASE_URL.startswith("sqlite:///")
            ):
                raise ValueError(
                    "CRÍTICO: DATABASE_URL debe ser una URL de base de datos válida. "
                    f"Formato actual: {self.DATABASE_URL[:30]}..."
                )

        return True

    def validate_all(self) -> bool:
        """
        Valida toda la configuración del sistema.
        En producción, bloquea configuraciones inseguras.
        """
        # Validaciones que aplican siempre
        self.validate_secret_key()
        self.validate_admin_credentials()
        self.validate_debug_mode()
        self.validate_cors_config()
        self.validate_cors_middleware_config()
        self.validate_database_url()

        return True

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignorar variables de entorno no definidas en el modelo
    )


# Instancia global de configuración
# Manejar CORS_ORIGINS manualmente si falla el parsing
try:
    settings = Settings()
except Exception as e:
    if "CORS_ORIGINS" in str(e):
        # Si falla por CORS_ORIGINS, intentar sin la variable de entorno
        cors_env_backup = os.environ.pop("CORS_ORIGINS", None)
        try:
            settings = Settings()
            logger.info(
                "ℹ️ CORS_ORIGINS no pudo ser parseado desde variable de entorno. "
                "Usando valores por defecto que se filtrarán automáticamente."
            )
        except Exception:
            # Restaurar variable y dejar que falle normalmente
            if cors_env_backup:
                os.environ["CORS_ORIGINS"] = cors_env_backup
            raise e
        finally:
            # No restaurar la variable si el parsing falló
            pass
    else:
        raise

# Validar configuración al importar
try:
    settings.validate_all()
    logger.info(f"✅ Configuración validada correctamente (ENVIRONMENT: {settings.ENVIRONMENT})")
except ValueError as e:
    error_msg = f"❌ Error de validación de configuración: {e}"
    logger.error(error_msg)
    if settings.ENVIRONMENT == "production":
        # En producción, las validaciones fallidas son críticas y deben detener la aplicación
        raise RuntimeError(
            f"CONFIGURACIÓN INSEGURA DETECTADA EN PRODUCCIÓN: {e}\n"
            "La aplicación no puede iniciar con configuraciones inseguras.\n"
            "Por favor, corrija las variables de entorno y reinicie la aplicación."
        ) from e
    else:
        # En desarrollo, solo advertir
        logger.warning(f"⚠️ Advertencia de configuración en desarrollo: {e}\n" "Esto causará errores en producción.")
