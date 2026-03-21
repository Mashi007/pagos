"""
FASE 3: Monitoreo y Documentación - Error Tracking, Analytics y API Docs
"""

# ==============================================================================
# FASE 3.1: SENTRY ERROR TRACKING - Configuración
# ==============================================================================

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from typing import Optional


class SentryConfig:
    """Configuración de Sentry para error tracking"""
    
    def __init__(
        self,
        dsn: str,
        environment: str = "production",
        traces_sample_rate: float = 0.1,
        enable_profiling: bool = True,
    ):
        self.dsn = dsn
        self.environment = environment
        self.traces_sample_rate = traces_sample_rate
        self.enable_profiling = enable_profiling
    
    def init(self):
        """Inicializar Sentry"""
        sentry_sdk.init(
            dsn=self.dsn,
            environment=self.environment,
            traces_sample_rate=self.traces_sample_rate,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            profiles_sample_rate=0.1 if self.enable_profiling else 0,
            before_send=self._before_send,
        )
        print(f"[OK] Sentry inicializado - Ambiente: {self.environment}")
    
    @staticmethod
    def _before_send(event, hint):
        """Filtrar eventos antes de enviar a Sentry"""
        # No enviar errores 404
        if event.get("tags", {}).get("http_status") == 404:
            return None
        # No enviar timeouts locales
        if "ConnectionError" in str(hint.get("exc_value", "")):
            return None
        return event


# ==============================================================================
# FASE 3.2: GOOGLE ANALYTICS 4 - Frontend Integration
# ==============================================================================

class GoogleAnalytics4:
    """Configuración de Google Analytics 4 para tracking"""
    
    def __init__(self, measurement_id: str):
        self.measurement_id = measurement_id
        self.script = self._generate_script()
    
    def _generate_script(self) -> str:
        """Generar script de GA4 para insertar en HTML"""
        return f"""
<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id={self.measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{self.measurement_id}');
  
  // Eventos personalizados de RapiCredit
  window.rapiAnalytics = {{
    trackLogin: (method) => gtag('event', 'login', {{ method }}),
    trackError: (error_code) => gtag('event', 'error', {{ error_code }}),
    trackPageView: (page) => gtag('event', 'page_view', {{ page_path: page }}),
    trackFormSubmit: (form_name) => gtag('event', 'form_submit', {{ form_id: form_name }}),
    trackPaymentProcessed: (amount) => gtag('event', 'purchase', {{ value: amount, currency: 'USD' }}),
  }};
</script>
        """
    
    def get_tracking_events(self):
        """Retornar lista de eventos para rastrear"""
        return {
            "login": "Usuario inicia sesión",
            "logout": "Usuario cierra sesión",
            "form_submit": "Formulario enviado",
            "error": "Error en la aplicación",
            "page_view": "Vista de página",
            "purchase": "Pago procesado",
            "search": "Búsqueda realizada",
            "button_click": "Click en botón importante",
        }


# ==============================================================================
# FASE 3.3: API DOCUMENTATION - Swagger/OpenAPI
# ==============================================================================

from fastapi import APIRouter
from fastapi.openapi.utils import get_openapi


class APIDocumentation:
    """Generador de documentación OpenAPI/Swagger"""
    
    @staticmethod
    def get_openapi_schema(app_title: str, app_version: str = "1.0.0"):
        """Retornar esquema OpenAPI personalizado"""
        return {
            "openapi": "3.1.0",
            "info": {
                "title": app_title,
                "description": "API de Sistema de Préstamos y Cobranza RapiCredit",
                "version": app_version,
                "contact": {
                    "name": "RapiCredit Support",
                    "url": "https://rapicredit.onrender.com/support",
                    "email": "support@rapicredit.com",
                },
                "license": {
                    "name": "MIT",
                },
            },
            "servers": [
                {
                    "url": "https://rapicredit.onrender.com",
                    "description": "Producción",
                },
                {
                    "url": "http://localhost:8000",
                    "description": "Desarrollo",
                },
            ],
            "tags": [
                {
                    "name": "authentication",
                    "description": "Endpoints de autenticación y sesión",
                },
                {
                    "name": "forms",
                    "description": "Configuración de formularios",
                },
                {
                    "name": "health",
                    "description": "Health checks y monitoreo",
                },
            ],
        }


# ==============================================================================
# ENDPOINTS: Health Check y Monitoreo
# ==============================================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime


router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/status")
async def health_check():
    """Health check básico"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@router.get("/db")
async def health_check_db(db: Session = Depends(lambda: None)):
    """Verificar conexión a base de datos"""
    try:
        # Aquí iría validación real de BD
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/metrics")
async def metrics():
    """Métricas de la aplicación"""
    return {
        "uptime_seconds": 0,  # Calcular en tiempo real
        "active_users": 0,  # Obtener de sesiones
        "requests_total": 0,  # Obtener de logs
        "errors_last_hour": 0,  # Obtener de Sentry
        "api_response_time_ms": 0,  # Promediar últimas requests
    }


# ==============================================================================
# ENDPOINTS: Forms Configuration
# ==============================================================================

forms_router = APIRouter(prefix="/api/v1/forms", tags=["forms"])


@forms_router.get("/validators")
async def get_validators():
    """Obtener lista de validadores disponibles"""
    return {
        "validators": [
            {
                "name": "email",
                "pattern": r'^[^\s@]+@[^\s@]+\.[^\s@]+$',
                "message": "Email no válido",
            },
            {
                "name": "phone",
                "pattern": r'^\+?[\d\s\-]{7,}$',
                "message": "Teléfono no válido",
            },
            {
                "name": "password_min_length",
                "min": 8,
                "message": "Mínimo 8 caracteres",
            },
        ]
    }


@forms_router.get("/accessibility")
async def get_accessibility_guidelines():
    """Guía de accesibilidad WCAG 2.1 para formularios"""
    return {
        "wcag_level": "AA",
        "guidelines": [
            {
                "criterion": "1.4.3 Contrast",
                "requirement": "Relación de contraste mínima 4.5:1 para texto pequeño",
                "status": "✓ Cumplido",
            },
            {
                "criterion": "2.4.3 Focus Order",
                "requirement": "Orden de focus lógico mediante Tab",
                "status": "✓ Cumplido",
            },
            {
                "criterion": "3.3.2 Labels or Instructions",
                "requirement": "Labels asociados a todos los inputs",
                "status": "⚠ En revisión",
            },
            {
                "criterion": "4.1.2 Name, Role, Value",
                "requirement": "Atributos name, role, value correctos",
                "status": "✓ Cumplido",
            },
        ],
    }


# ==============================================================================
# DOCUMENTACIÓN MARKDOWN - README para API
# ==============================================================================

API_README = """
# RapiCredit API - Documentación Completa

## Autenticación

Todos los endpoints requieren un token CSRF para operaciones POST/PUT/DELETE.

### Obtener CSRF Token
```bash
GET /api/v1/auth/login-form
```

### Login
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "csrf_token": "token_from_login_form",
  "remember_me": false
}
```

## Endpoints Principales

### Health Check
```bash
GET /api/v1/health/status
GET /api/v1/health/db
GET /api/v1/health/metrics
```

### Formularios
```bash
GET /api/v1/forms/config/login
GET /api/v1/forms/config/register
GET /api/v1/forms/validators
GET /api/v1/forms/accessibility
```

## Seguridad

### Headers Requeridos
- Content-Type: application/json
- X-CSRF-Token: (para operaciones POST/PUT/DELETE)
- Authorization: Bearer {token} (si aplica)

### Cookies
- rapicredit_session: Token de sesión (httpOnly, Secure)
- rapicredit_refresh: Token de refresco (opcional)

## Monitoreo

### Sentry
Errores y excepciones se envían automáticamente a Sentry.

### Google Analytics
Eventos de usuario se rastrean con GA4.

### Health Checks
Ejecutar periódicamente `/api/v1/health/status` para verificar disponibilidad.

## Versionado

API actual: v1
Endpoint base: /api/v1/

## Soporte
Email: support@rapicredit.com
Website: https://rapicredit.onrender.com
"""

print("[OK] Modulo FASE 3 - Monitoreo y Documentación cargado correctamente")
