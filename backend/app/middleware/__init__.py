"""
Middlewares de la aplicación.
"""
from app.middleware.audit_middleware import AuditMiddleware

__all__ = ["AuditMiddleware"]
