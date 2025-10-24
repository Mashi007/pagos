# backend/app/core/security_audit.py
"""
Security Audit Logger - Logging de eventos de seguridad críticos
Cumple con OWASP A09:2021 - Security Logging and Monitoring Failures
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
from enum import Enum

# Configurar logger específico para auditoría de seguridad
security_audit_logger = logging.getLogger("security_audit")

class SecurityEventType(str, Enum):
    """Tipos de eventos de seguridad"""
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET = "PASSWORD_RESET"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    DATA_MODIFICATION = "DATA_MODIFICATION"
    ADMIN_ACTION = "ADMIN_ACTION"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"

# Logger especializado para auditoría de seguridad
security_audit_logger = logging.getLogger("security_audit")

def log_security_event(
    event_type: SecurityEventType,
    user_email: Optional[str] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True
):
    """
    Registra un evento de seguridad

    Args:
        event_type: Tipo de evento de seguridad
        user_email: Email del usuario (si aplica)
        user_id: ID del usuario (si aplica)
        ip_address: Dirección IP de origen
        details: Detalles adicionales del evento
        success: Si la acción fue exitosa o no
    """
    event_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type.value,
        "user_email": user_email,
        "user_id": user_id,
        "ip_address": ip_address,
        "success": success,
        "details": details or {}
    }

    # Nivel de log según tipo de evento
    if not success or event_type in [
        SecurityEventType.LOGIN_FAILED,
        SecurityEventType.UNAUTHORIZED_ACCESS,
        SecurityEventType.RATE_LIMIT_EXCEEDED,
        SecurityEventType.SUSPICIOUS_ACTIVITY
    ]:
        security_audit_logger.warning(f"SECURITY EVENT: {event_data}")
    else:
        security_audit_logger.info(f"SECURITY EVENT: {event_data}")

def log_login_attempt(
    email: str,
    ip_address: str,
    success: bool,
    reason: Optional[str] = None
):
    """Registra un intento de login"""
    log_security_event(
        event_type=SecurityEventType.LOGIN_SUCCESS if success else SecurityEventType.LOGIN_FAILED,
        user_email=email,
        ip_address=ip_address,
        details={"reason": reason} if reason else None,
        success=success
    )

def log_password_change(
    user_email: str,
    user_id: int,
    ip_address: str,
    success: bool
):
    """Registra un cambio de contraseña"""
    log_security_event(
        event_type=SecurityEventType.PASSWORD_CHANGE,
        user_email=user_email,
        user_id=user_id,
        ip_address=ip_address,
        success=success
    )

def log_unauthorized_access(
    endpoint: str,
    user_email: Optional[str],
    ip_address: str,
    reason: str
):
    """Registra un intento de acceso no autorizado"""
    log_security_event(
        event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
        user_email=user_email,
        ip_address=ip_address,
        details={"endpoint": endpoint, "reason": reason},
        success=False
    )

def log_data_modification(
    user_email: str,
    user_id: int,
    resource: str,
    resource_id: int,
    action: str,
    ip_address: str
):
    """Registra modificación de datos sensibles"""
    log_security_event(
        event_type=SecurityEventType.DATA_MODIFICATION,
        user_email=user_email,
        user_id=user_id,
        ip_address=ip_address,
        details={
            "resource": resource,
            "resource_id": resource_id,
            "action": action
        }
    )

