"""
Middleware de Seguridad - Headers y Content Security Policy
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import uuid
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware que agrega headers de seguridad recomendados por OWASP.
    
    Previene:
    - X-Content-Type-Options: Sniffing de MIME types
    - X-Frame-Options: Clickjacking
    - X-XSS-Protection: XSS injection (navegadores antiguos)
    - Referrer-Policy: Leakage de información sensible
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # X-Content-Type-Options: Previene MIME type sniffing
        # Fuerza al navegador a usar el Content-Type declarado
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Previene clickjacking
        # Valores: DENY | SAMEORIGIN | ALLOW-FROM url
        # DENY = No permitir en iframes
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Prevención de XSS en navegadores antiguos
        # 1; mode=block = Bloquea la página si detecta XSS
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy: Controla qué información se envía en Referer header
        # strict-origin-when-cross-origin = Solo envía origen en cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy: Controla qué APIs puede usar el navegador
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        return response


class ContentSecurityPolicyMiddleware(BaseHTTPMiddleware):
    """
    Middleware que implementa Content Security Policy (CSP).
    
    CSP define qué recursos (scripts, estilos, imágenes, etc) pueden cargarse.
    Previene ataques XSS bloqueando inline scripts y recursos maliciosos.
    
    Directivas implementadas:
    - default-src 'self': Por defecto, solo recursos del mismo origen
    - script-src: Scripts solo del mismo origen + nonce
    - style-src: Estilos solo del mismo origen + nonce
    - img-src: Imágenes de mismo origen + https + data + blob (previews)
    - font-src: Fuentes del mismo origen
    - connect-src: Conexiones API al backend
    - frame-src: No permitir iframes
    - object-src: No permitir plugins
    - base-uri: Restringir <base> tag
    - form-action: Formularios solo al mismo origen
    - frame-ancestors: No permitir incrustación en otros sitios
    - upgrade-insecure-requests: Convertir HTTP → HTTPS automáticamente
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # Base CSP Policy
        self.csp_policy = " ".join([
            # Default policy
            "default-src 'self'",
            
            # Scripts: solo self + nonce (para scripts inline)
            "script-src 'self'",
            
            # Styles: solo self + nonce + unsafe-hashes para inline
            "style-src 'self' 'unsafe-hashes'",
            
            # Images: self + https externo (para CDN)
            "img-src 'self' https: data: blob:",
            
            # Fonts: solo self
            "font-src 'self'",
            
            # Conexiones: self + backend API
            "connect-src 'self'",
            
            # Media: solo self
            "media-src 'self'",
            
            # No permitir iframes
            "frame-src 'none'",
            
            # No permitir plugins
            "object-src 'none'",
            
            # Restringir tag <base>
            "base-uri 'self'",
            
            # Formularios solo al mismo origen
            "form-action 'self'",
            
            # No permitir incrustación en otros sitios
            "frame-ancestors 'none'",
            
            # Upgrade HTTP a HTTPS automáticamente
            "upgrade-insecure-requests",
            
            # Reportar violaciones de CSP
            # "report-uri /api/v1/security/csp-report",
        ])
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Agregar CSP header
        response.headers["Content-Security-Policy"] = self.csp_policy
        
        # Report-Only: No bloquea, solo reporta violaciones (útil para testing)
        # response.headers["Content-Security-Policy-Report-Only"] = self.csp_policy
        
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware que agrega un ID único a cada request para trazabilidad.
    
    Útil para correlacionar logs y debugging.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware que configura CORS de forma segura.
    
    Restringe qué orígenes pueden hacer requests cross-origin.
    """
    
    def __init__(self, app, allowed_origins: list = None):
        super().__init__(app)
        
        # Por defecto, solo localhost en desarrollo
        self.allowed_origins = allowed_origins or [
            "http://localhost:3000",
            "http://localhost:8000",
            "https://rapicredit.onrender.com",
            "https://pagos-f2qf.onrender.com",
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")
        
        response = await call_next(request)
        
        if origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRF-Token"
            response.headers["Access-Control-Max-Age"] = "3600"
        
        return response
