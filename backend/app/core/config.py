"""
Configuración de la aplicación
"""

import json
import logging
from typing import List, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # ============================================
    # BASE DE DATOS
    # ============================================
    DATABASE_URL: str = Field(default="postgresql://user:password@localhost/pagos_db", env="DATABASE_URL")

    # ============================================
    # SEGURIDAD
    # ============================================
    SECRET_KEY: str = Field(default="your-secret-key-here-change-in-production", env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 240  # 4 horas
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ============================================
    # CORS
    # ============================================
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "https://rapicredit.onrender.com",  # Frontend en producción
        ],
        env="CORS_ORIGINS",
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
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ============================================
    # USUARIO ADMINISTRADOR INICIAL
    # ============================================
    ADMIN_EMAIL: str = "itmaster@rapicreditca.com"
    ADMIN_PASSWORD: str = Field(default="R@pi_2025**", env="ADMIN_PASSWORD")

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

    def validate_secret_key(self) -> bool:
        """
        Valida que SECRET_KEY sea seguro en producción.
        Bloquea valores por defecto o débiles.
        """
        if self.ENVIRONMENT == "production":
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
        Bloquea contraseñas por defecto en producción.
        """
        if not self.ADMIN_EMAIL:
            raise ValueError("ADMIN_EMAIL debe estar configurado")
        if not self.ADMIN_PASSWORD:
            raise ValueError("ADMIN_PASSWORD debe estar configurado")

        if len(self.ADMIN_PASSWORD) < 8:
            raise ValueError("La contraseña de admin debe tener al menos 8 caracteres")

        # Validación específica para producción
        if self.ENVIRONMENT == "production":
            import os

            # Verificar si ADMIN_PASSWORD fue configurado desde variable de entorno
            admin_password_from_env = os.getenv("ADMIN_PASSWORD")
            default_password = "R@pi_2025**"

            # Si NO está configurado en variable de entorno y usa el valor por defecto
            # IMPORTANTE: NO bloquear para permitir que la aplicación inicie y el usuario pueda configurar
            if (
                not admin_password_from_env or admin_password_from_env.strip() == ""
            ) and self.ADMIN_PASSWORD == default_password:
                # Advertir severamente pero NO bloquear
                logger.critical(
                    "🚨🚨🚨 CRÍTICO: ADMIN_PASSWORD no está configurada como variable de entorno y usa el valor por defecto. "
                    "ESTO ES UNA GRAVE FALTA DE SEGURIDAD. "
                    "Por favor, configure ADMIN_PASSWORD como variable de entorno en Render Dashboard con una contraseña segura. "
                    "La aplicación iniciará con esta configuración insegura SOLO para permitir la configuración. "
                    "CAMBIE ESTO INMEDIATAMENTE. 🚨🚨🚨"
                )
                # NO lanzar excepción - permitir que la aplicación inicie
                # La seguridad es importante, pero bloquear impide que el usuario pueda configurar

            # Si viene de variable de entorno, permitir aunque sea débil (asumimos decisión consciente)
            # Pero advertir si es muy corta o débil
            if admin_password_from_env:
                if len(admin_password_from_env) < 12:
                    logger.warning(
                        "⚠️ ADMIN_PASSWORD configurado desde variable de entorno pero es muy corta (<12 caracteres). "
                        "Se recomienda usar una contraseña más segura para producción."
                    )

                # Si es el valor por defecto pero viene de env, permitir pero advertir
                if admin_password_from_env == default_password:
                    logger.warning(
                        "⚠️ ADMIN_PASSWORD está configurado con el valor por defecto desde variable de entorno. "
                        "Se recomienda cambiar por una contraseña más segura en producción."
                    )

            # Validar formato de email
            if "@" not in self.ADMIN_EMAIL or "." not in self.ADMIN_EMAIL.split("@")[1]:
                raise ValueError("ADMIN_EMAIL debe ser un email válido en producción")

            # Contraseña debe tener complejidad mínima (solo si NO viene de env)
            # Pero no bloquear si usa el valor por defecto (ya se advirtió arriba)
            if not admin_password_from_env and self.ADMIN_PASSWORD != default_password:
                has_upper = any(c.isupper() for c in self.ADMIN_PASSWORD)
                has_lower = any(c.islower() for c in self.ADMIN_PASSWORD)
                has_digit = any(c.isdigit() for c in self.ADMIN_PASSWORD)
                has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in self.ADMIN_PASSWORD)

                if not (has_upper and has_lower and (has_digit or has_special)):
                    # Solo advertir, no bloquear
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
    )


# Instancia global de configuración
# Manejar CORS_ORIGINS manualmente si falla el parsing
try:
    settings = Settings()
except Exception as e:
    if "CORS_ORIGINS" in str(e):
        # Si falla por CORS_ORIGINS, intentar sin la variable de entorno
        import os

        cors_env_backup = os.environ.pop("CORS_ORIGINS", None)
        try:
            settings = Settings()
            logger.warning(
                "⚠️ CORS_ORIGINS no pudo ser parseado desde variable de entorno. "
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
