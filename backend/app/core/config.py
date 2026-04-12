"""
Configuración del sistema usando Pydantic Settings
"""
import json
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # ============================================
    # Configuración General
    # ============================================
    PROJECT_NAME: str = "Sistema de Pagos"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Si True, expone /docs, /redoc y /openapi.json. En produccion dejar False salvo necesidad explicita.
    ENABLE_OPENAPI_DOCS: bool = Field(
        default=False,
        description="Expone documentacion OpenAPI en /docs y /redoc. Produccion: False. Desarrollo: True o DEBUG=True.",
    )
    # Por defecto False: ningun job programado al arrancar (APScheduler, liquidado 21:00, cache dashboard).
    # Poner True en .env solo si se desean tareas automaticas en segundo plano (no disparadas al guardar Configuracion).
    ENABLE_AUTOMATIC_SCHEDULED_JOBS: bool = Field(
        default=False,
        description=(
            "Si True, el proceso lider puede iniciar APScheduler (finiquito, auditoria cartera, limpieza codigos, "
            "Gmail programado si aplica), liquidado diario 21:00 Caracas, refresco programado de cache del dashboard, "
            "watcher de lider y, al arrancar, marcar syncs Gmail 'running' como error (desbloqueo tras deploy). "
            "A las 03:00 America/Caracas puede ejecutarse el envio automatico exclusivo PAGO_2_DIAS_ANTES_PENDIENTE "
            "si en BD notificaciones_envios.cron_envio_pago_2_dias_antes.habilitado esta activo (submenu 2 dias antes). "
            "Por defecto False: ejecucion manual desde la aplicacion; sin limpieza automatica de Gmail al startup."
        ),
    )
    
    # ============================================
    # Base de Datos
    # ============================================
    DATABASE_URL: str = Field(
        ...,
        description="URL de conexión a PostgreSQL"
    )
    # Pool por proceso (cada worker de Gunicorn tiene su propio engine). Subir si el dashboard
    # dispara muchas peticiones lentas en paralelo y aparece: QueuePool limit ... overflow ... reached.
    # Respetar max_connections de Postgres (ej. 2 workers × (pool + overflow) < límite del servidor).
    DATABASE_POOL_SIZE: int = Field(
        default=10,
        ge=1,
        le=80,
        description="Conexiones persistentes del pool SQLAlchemy por worker",
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=20,
        ge=0,
        le=80,
        description="Conexiones extra bajo pico (máx por worker ≈ pool_size + max_overflow)",
    )
    DATABASE_POOL_TIMEOUT: int = Field(
        default=60,
        ge=5,
        le=300,
        description="Segundos esperando conexión libre antes de sqlalchemy.exc.TimeoutError",
    )

    # ============================================
    # Seguridad
    # ============================================
    SECRET_KEY: str = Field(
        ...,
        description="Clave secreta para JWT"
    )
    ALGORITHM: str = "HS256"
    # Access token: duración en minutos. Override con ACCESS_TOKEN_EXPIRE_MINUTES en .env (ej. 240 = 4 horas).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=240,
        description="Minutos hasta que expire el access token (default 4h). El refresh token sigue 7 días."
    )
    # Refresh token: duración en días (solo para renovar access token; no obliga a login hasta que expire).
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Días hasta que expire el refresh token")
    REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS: int = Field(default=30, description="Dias del access token cuando Recordarme esta activo")
    REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=90, description="Dias del refresh token cuando Recordarme esta activo")

    # Usuario admin único (auth sin tabla users). Opcional.
    ADMIN_EMAIL: Optional[str] = Field(None, description="Email del usuario admin para login")
    ADMIN_PASSWORD: Optional[str] = Field(None, description="Contraseña del usuario admin para login")
    # Secreto para endpoint interno de restablecer contraseña (sincronizar usuario BD con ADMIN_PASSWORD).
    RESET_PASSWORD_SECRET: Optional[str] = Field(None, description="Secreto para POST /api/v1/auth/admin/reset-password (header X-Admin-Secret)")
    # Secreto para ejecutar migración auditoria FK (POST /admin/run-migration-auditoria-fk con header X-Migration-Secret)
    MIGRATION_AUDITORIA_SECRET: Optional[str] = Field(None, description="Secreto para ejecutar migración auditoria FK (una sola vez)")
    # Email al que se envía la notificación cuando un usuario solicita "Olvidé mi contraseña" (para envío de nueva).
    FORGOT_PASSWORD_NOTIFY_EMAIL: str = Field(
        default="itmaster@rapicreditca.com",
        description="Destino del correo de solicitud de restablecimiento de contraseña",
    )
    # False = exige JWT cobros_public (OTP por correo) en validar-cedula y enviar-reporte publicos.
    COBROS_PUBLICO_OTP_DISABLED: bool = Field(
        default=True,
        description="Por defecto True: rapicredit-cobros sin codigo al correo. Poner False para exigir OTP.",
    )
    
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        """Validar que SECRET_KEY tenga longitud y complejidad adecuadas"""
        if len(v) < 32:
            raise ValueError('SECRET_KEY debe tener al menos 32 caracteres para seguridad adecuada')
        # Validar que no sea un valor común o débil
        weak_keys = ['secret', 'password', '123456', 'admin', 'test', 'dev', 'development']
        if v.lower() in weak_keys or len(set(v)) < 8:
            raise ValueError('SECRET_KEY debe ser una cadena aleatoria y segura, no un valor común')
        return v
    
    # ============================================
    # Encriptación (API keys, contraseñas en BD)
    # ============================================
    ENCRYPTION_KEY: Optional[str] = Field(
        None,
        description="Clave de encriptación Fernet para valores sensibles en BD (API keys, contraseñas). Generar con: from cryptography.fernet import Fernet; Fernet.generate_key().decode()"
    )
    
    # ============================================
    # WhatsApp / Meta API
    # ============================================
    WHATSAPP_VERIFY_TOKEN: Optional[str] = Field(
        None,
        description="Token de verificación del webhook de WhatsApp (Meta)"
    )
    WHATSAPP_ACCESS_TOKEN: Optional[str] = Field(
        None,
        description="Access Token de WhatsApp Business API (Meta)"
    )
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = Field(
        None,
        description="Phone Number ID de WhatsApp Business"
    )
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = Field(
        None,
        description="Business Account ID de WhatsApp"
    )
    WHATSAPP_APP_SECRET: Optional[str] = Field(
        None,
        description="App Secret de Meta para verificar firma de webhooks (recomendado)"
    )

    # URL para aviso cuando el webhook de WhatsApp falla (ej. Slack Incoming Webhook).
    # Si está configurada, se envía un POST con el mensaje de error.
    ALERT_WEBHOOK_URL: Optional[str] = Field(
        None,
        description="URL (ej. Slack Incoming Webhook) para alertas cuando falla el procesamiento del webhook de WhatsApp"
    )
    # Teléfono de soporte mostrado cuando el usuario supera máx intentos (cédula inválida, etc.).
    SUPPORT_PHONE: str = Field(
        default="0424-4359435",
        description="Teléfono de soporte para estado ERROR_MAX_INTENTOS del bot de cobranza",
    )
    # Segundos de espera entre mensajes del bot (humanización: simular "escribiendo"). Spec: 2.
    MESSAGE_DELAY_SECONDS: float = Field(
        default=2.0,
        description="Delay en segundos entre mensajes consecutivos del bot (bienvenida en varios mensajes)",
    )
    
    # ============================================
    # Email
    # ============================================
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    # Remitente forzado para el servicio "notificaciones" (rechazos, notificaciones a clientes). Si está definido, se usa como From al enviar con servicio=notificaciones.
    NOTIFICACIONES_FROM_EMAIL: Optional[str] = Field(
        default="notificaciones@rapicreditca.com",
        description="Email remitente para notificaciones (rechazos, etc.). Por defecto notificaciones@rapicreditca.com.",
    )
    # Solo PAGO_2_DIAS_ANTES / tipo_tab d_2_antes_vencimiento (tiene prioridad sobre NOTIFICACIONES_FROM_EMAIL).
    NOTIFICACIONES_FROM_EMAIL_2_DIAS_ANTES: str = Field(
        default="recuerda@rapicreditca.com",
        description=(
            "Remitente From para «2 dias antes» (d_2_antes_vencimiento). "
            "Valor vacío en .env se sustituye por recuerda@rapicreditca.com en el holder SMTP."
        ),
    )
    # Correo(s) para notificaciones de tickets CRM (varios separados por coma). Incluye tickets automáticos por recibo no claro (3 intentos).
    TICKETS_NOTIFY_EMAIL: Optional[str] = Field(
        default="itmaster@rapicreditca.com",
        description="Email(s) para notificar cuando se crea o actualiza un ticket (separados por coma). Por defecto itmaster@rapicreditca.com."
    )
    # URL pública del frontend (para enlaces y logo en emails de cobranza). Ej: https://rapicredit.onrender.com/pagos
    FRONTEND_PUBLIC_URL: Optional[str] = Field(
        default="https://rapicredit.onrender.com/pagos",
        description="URL base del frontend para imágenes en emails (logo RapiCredit).",
    )
    # Ruta al logo PNG para generar el PDF de carta de cobranza (adjunto al email). Opcional; si no existe se omite el logo en el PDF.
    LOGO_PDF_COBRANZA_PATH: Optional[str] = Field(
        None,
        description="Ruta absoluta al archivo PNG del logo para el PDF de carta de cobranza.",
    )
    # Directorio base para el PDF fijo de cobranza. Si está definido, la ruta guardada en configuracion se resuelve dentro de este directorio (evita path traversal).
    ADJUNTO_FIJO_COBRANZA_BASE_DIR: Optional[str] = Field(
        None,
        description="Directorio base donde se buscan los PDFs fijos de cobranza. La ruta en BD se interpreta como relativa a este directorio. Ej: /var/app/adjuntos_cobranza",
    )
    # Si True (defecto), no se envia correo de notificacion por cuota sin: plantilla email activa, PDF Carta_Cobranza valido y al menos un PDF fijo. Poner False solo en emergencia (.env).
    NOTIFICACIONES_PAQUETE_ESTRICTO: bool = Field(
        default=True,
        description="Exige plantilla + PDF variable (carta) + PDF fijo antes de enviar notificaciones por pestaña",
    )
    # Si True: solo con destinos forzados (prueba de paquete) permite enviar aunque falte PDF fijo.
    NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO: bool = Field(
        default=False,
        description=(
            'Relaja validacion de paquete solo para POST /enviar-prueba-paquete (destinos forzados). '
            'Los envios masivos reales siguen sujetos a NOTIFICACIONES_PAQUETE_ESTRICTO.'
        ),
    )
    # Cartera / liquidacion: si True, no marcar LIQUIDADO hasta cuadrar suma pagos operativos vs cuota_pagos (tol 0.02 USD, mismo criterio que auditoria).
    LIQUIDACION_REQUIERE_CUADRE_PAGOS_VS_CUOTAS: bool = Field(
        default=False,
        description=(
            "Si True: no marcar prestamo LIQUIDADO hasta que suma pagos operativos y suma aplicada en "
            "cuota_pagos cuadren (0.02 USD). Por defecto False: basta cobertura de cuotas."
        ),
    )
    # Pagos BS: si monto_pagado (en Bs.) >= este valor, no se exige cedula en cedulas_reportar_bs.
    # Alinear operativamente con la heuristica de carga masiva (monto alto en Excel tratado como Bs.).
    PAGOS_BS_MONTO_EXENTO_LISTA_CEDULA: int = Field(
        default=10000,
        ge=1,
        le=999_999_999,
        description=(
            "Umbral en bolivares: pagos en BS con monto >= este valor omiten validacion de lista "
            "cedulas_reportar_bs (sigue exigiendo cliente en BD y tasa)."
        ),
    )

    # ============================================
    # AI / OpenRouter (clave solo en backend, nunca en frontend)
    # ============================================
    OPENROUTER_API_KEY: Optional[str] = Field(
        None,
        description="API Key de OpenRouter. Configurar en variables de entorno del dashboard (Render, etc.). Nunca se expone al frontend."
    )
    OPENROUTER_MODEL: Optional[str] = Field(
        default="openai/gpt-4o-mini",
        description="Modelo por defecto para chat/completions. Ej: openai/gpt-4o-mini, google/gemini-2.0-flash-001, anthropic/claude-3-5-haiku"
    )

    # ============================================
    # Redis (Cache)
    # ============================================
    REDIS_URL: Optional[str] = Field(
        None,
        description="URL de conexión a Redis (opcional)"
    )
    
    # ============================================
    # Sentry (Monitoreo)
    # ============================================
    SENTRY_DSN: Optional[str] = Field(
        None,
        description="DSN de Sentry para monitoreo (opcional)"
    )
    
    # ============================================
    # Google OAuth (Drive/Sheets cuando no hay cuenta de servicio)
    # ============================================
    BACKEND_PUBLIC_URL: Optional[str] = Field(
        None,
        description="URL pública del backend para OAuth redirect_uri (ej. https://rapicredit.onrender.com)"
    )
    FRONTEND_PUBLIC_URL: Optional[str] = Field(
        None,
        description="URL pública del frontend (SPA). Tras OAuth Google se redirige aquí/pagos/configuracion?tab=informe-pagos. Si no se define, se usa BACKEND_PUBLIC_URL (mismo origen)."
    )

    # ============================================

    # ============================================
    # Gmail / Drive / Sheets / Gemini (pagos desde correo)
    # ============================================
    GOOGLE_CLIENT_ID: Optional[str] = Field(None, description="OAuth 2.0 Client ID para Gmail/Drive/Sheets")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(None, description="OAuth 2.0 Client Secret")
    GOOGLE_REDIRECT_URI: Optional[str] = Field(None, description="Redirect URI tras autorizar Gmail (ej. https://tu-backend/api/v1/pagos/gmail/callback)")
    GMAIL_TOKENS_PATH: str = Field(default="gmail_tokens.json", description="Ruta al JSON con access/refresh tokens")
    GEMINI_API_KEY: Optional[str] = Field(None, description="API Key de Google AI Studio para Gemini")
    DRIVE_ROOT_FOLDER_ID: str = Field(default="1uzFPzUo00urjiWmeql1F30xgwpjdhm2o", description="ID carpeta raiz Drive para adjuntos")
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Modelo Gemini para extracción de datos. gemini-2.5-flash es la versión estable recomendada. Ver https://ai.google.dev/gemini-api/docs/models",
    )
    PAGOS_GMAIL_DOWNLOAD_EXCEL_MAX_ITEMS: int = Field(
        default=0,
        description="Máximo de filas al descargar Excel sin fecha (evita memoria/timeout). Con ?fecha= no aplica límite por día.",
    )
    PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED: bool = Field(
        default=False,
        description=(
            "Si True y ENABLE_AUTOMATIC_SCHEDULED_JOBS=True, el scheduler ejecuta el pipeline Gmail "
            "a las 4:00, 11:00 y 20:00 (America/Caracas). Por defecto False: solo ejecucion manual."
        ),
    )
    PAGOS_GMAIL_UNREAD_MAX_PASSES: int = Field(
        default=30,
        ge=1,
        le=100,
        description=(
            "Obsoleto: el pipeline ya no hace pasadas multiples por no leidos (unread/read/all listan inbox completo). "
            "Se conserva por compatibilidad en .env; el codigo no lo usa."
        ),
    )

    # Google Sheet CONCILIACIÓN → BD (snapshot diario vía cron, ej. 03:00 America/Caracas)
    CONCILIACION_SHEET_SPREADSHEET_ID: Optional[str] = Field(
        default=None,
        description="ID del documento (segmento entre /d/ e /edit en la URL de Google Sheets).",
    )
    CONCILIACION_SHEET_TAB_NAME: str = Field(
        default="CONCILIACIÓN",
        description="Nombre exacto de la pestaña a sincronizar.",
    )
    CONCILIACION_SHEET_HEADER_MARKER: str = Field(
        default="LOTE",
        description=(
            "Texto exacto (sin distinguir mayúsculas) de la celda de título que marca la fila de cabecera. "
            "Se busca en las primeras 26 columnas del rango leído y en las primeras 80 filas (p. ej. LOTE en B si A es numerador)."
        ),
    )
    CONCILIACION_SHEET_SYNC_SECRET: Optional[str] = Field(
        default=None,
        description="Secreto para POST /api/v1/conciliacion-sheet/sync (header X-Conciliacion-Sheet-Sync-Secret).",
    )
    CONCILIACION_SHEET_COLUMNS_RANGE: str = Field(
        default="A:S",
        description=(
            "Solo letras de columnas (ej. A:S). La lectura se ancla a fila 1 del sheet (A1:S en la API) "
            "para no omitir filas iniciales vacías y alinear la fila del marcador LOTE."
        ),
    )
    # Tasa USD/Bs Venezuela (reporte contable)
    # ============================================
    TASA_USD_BS_DEFAULT: Optional[float] = Field(
        None,
        description="Tasa USD a Bolívares (Venezuela) por defecto cuando la API externa no responde. Si no se configura, se usa la tasa actual de exchangerate-api.com."
    )
    EXCHANGERATE_API_URL: str = Field(
        default="https://api.exchangerate-api.com/v4/latest/USD",
        description="URL para obtener tasa USD actual (gratuita, sin API key). Para tasas históricas por fecha, configurar BCV_API_KEY."
    )

    # ============================================
    # CORS
    # ============================================
    CORS_ORIGINS: Optional[str] = Field(
        default='["http://localhost:3000", "http://localhost:5173", "https://pagos-f2qf.onrender.com", "https://rapicredit.onrender.com"]',
        description="Lista de orígenes permitidos para CORS (formato JSON o separado por comas). Incluye desarrollo y producción."
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Retorna CORS_ORIGINS como lista"""
        if not self.CORS_ORIGINS or self.CORS_ORIGINS.strip() == '':
            return ["http://localhost:3000", "http://localhost:5173", "https://pagos-f2qf.onrender.com", "https://rapicredit.onrender.com"]
        
        # Intentar parsear como JSON
        try:
            parsed = json.loads(self.CORS_ORIGINS)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        
        # Si no es JSON válido, tratar como string separado por comas
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignorar variables extra del .env no definidas en Settings


# Instancia global de settings
settings = Settings()
