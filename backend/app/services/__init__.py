# backend/app/services/__init__.py

from .auth_service import AuthService
from .email_service import EmailService
from .whatsapp_service import WhatsAppService

# Import condicional de MLService para evitar errores si scikit-learn no está instalado
try:
    from .ml_service import MLService

    __all__ = [
        "AuthService",
        "EmailService",
        "MLService",
        "WhatsAppService",
    ]
except ImportError:
    # Si scikit-learn no está disponible, MLService no se exporta
    __all__ = [
        "AuthService",
        "EmailService",
        "WhatsAppService",
    ]
