# typing import Any, Dict, Optional# Configurar logger específico para auditoría de seguridadsecurity_audit_logger =
# "LOGIN_SUCCESS" LOGIN_FAILED = "LOGIN_FAILED" LOGOUT = "LOGOUT" PASSWORD_CHANGE = "PASSWORD_CHANGE" PASSWORD_RESET =
# "PASSWORD_RESET" TOKEN_REFRESH = "TOKEN_REFRESH" UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS" RATE_LIMIT_EXCEEDED =
# "RATE_LIMIT_EXCEEDED" DATA_MODIFICATION = "DATA_MODIFICATION" ADMIN_ACTION = "ADMIN_ACTION" SUSPICIOUS_ACTIVITY =
# "SUSPICIOUS_ACTIVITY"# Logger especializado para auditoría de seguridadsecurity_audit_logger =
# logging.getLogger("security_audit")def log_security_event
# True,): """ Registra un evento de seguridad Args: event_type: Tipo de evento de seguridad user_email: Email del usuario 
# aplica) user_id: ID del usuario (si aplica) ip_address: Dirección IP de origen details: Detalles adicionales del evento
# event_type.value, "user_email": user_email, "user_id": user_id, "ip_address": ip_address, "success": success, "details":
# details or {}, } # Nivel de log según tipo de evento if not success or event_type in [ SecurityEventType.LOGIN_FAILED,
# SecurityEventType.UNAUTHORIZED_ACCESS, SecurityEventType.RATE_LIMIT_EXCEEDED, SecurityEventType.SUSPICIOUS_ACTIVITY, ]:
# security_audit_logger.warning(f"SECURITY EVENT: {event_data}") else: security_audit_logger.info
# {event_data}")def log_login_attempt( email: str, ip_address: str, success: bool, reason: Optional[str] = None): """Registra
# un intento de login""" log_security_event
# SecurityEventType.LOGIN_FAILED ), user_email=email, ip_address=ip_address, details={"reason": reason} if reason else None,
# success=success, )def log_password_change( user_email: str, user_id: int, ip_address: str, success: bool): """Registra un
# cambio de contraseña""" log_security_event
# user_id=user_id, ip_address=ip_address, success=success, )def log_unauthorized_access
# Optional[str], ip_address: str, reason: str): """Registra un intento de acceso no autorizado""" log_security_event
# endpoint, "reason": reason}, success=False, )def log_data_modification
# "resource": resource, "resource_id": resource_id, "action": action, }, )

"""