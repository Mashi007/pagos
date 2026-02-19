"""
Holder de configuración de email en tiempo de ejecución.
Usado por core/email.py para enviar (SMTP) y por tickets para destinos de notificación.
La API configuracion/email actualiza este holder al guardar; si no se ha guardado, se usan settings (.env).
Para que Notificaciones/CRM usen la config guardada en BD, sync_from_db() carga desde la tabla configuracion antes de enviar.

Integración con encriptación:
- Campos sensibles (smtp_password, etc.) se encriptan al guardar en BD
- Se desencriptan automáticamente al cargar desde BD
- Al devolver al API, se enmascaran (no se expone la contraseña)
"""
import json
from typing import Any, List, Optional, Tuple

from app.core.config import settings

# Config actual: smtp_*, from_email, from_name, tickets_notify_emails (str, emails separados por coma)
_current: dict[str, Any] = {}

CLAVE_EMAIL_CONFIG = "email_config"
CLAVE_NOTIFICACIONES_ENVIOS = "notificaciones_envios"

# Campos sensibles que deben encriptarse en BD
SENSITIVE_FIELDS = {"smtp_password"}


def _mask_sensitive_value(value: Any) -> str:
    """Enmascara un valor sensible para devolver a la API (no exponer contraseña)."""
    if not value:
        return ""
    return "***"


def _should_encrypt_field(field_name: str) -> bool:
    """Devuelve True si el campo debe encriptarse."""
    return field_name in SENSITIVE_FIELDS


def _decrypt_value_safe(encrypted: Any) -> Optional[str]:
    """Intenta desencriptar un valor; devuelve None si falla."""
    if not encrypted:
        return None
    try:
        from app.core.crypto import decrypt_value
        if isinstance(encrypted, bytes):
            return decrypt_value(encrypted)
        elif isinstance(encrypted, str):
            return decrypt_value(encrypted.encode('utf-8'))
    except Exception:
        # Si desencriptación falla, devolver None (posiblemente no estaba encriptado)
        return None
    return None


def _encrypt_value_safe(value: str) -> Optional[bytes]:
    """Intenta encriptar un valor; devuelve None si falla."""
    if not value or not _should_encrypt_field("smtp_password"):  # Solo si encryption está configurado
        return None
    try:
        from app.core.crypto import encrypt_value
        return encrypt_value(value)
    except Exception:
        # Si encryption no está configurado, retornar None (guardar sin encriptar)
        return None
    return None


def sync_from_db() -> None:
    """Carga la configuración de email desde la tabla configuracion y actualiza el holder. Así Notificaciones/CRM usan la config guardada en Configuración > Email."""
    try:
        from app.core.database import SessionLocal
        from app.models.configuracion import Configuracion
        db = SessionLocal()
        try:
            row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
            if row and row.valor:
                data = json.loads(row.valor)
                if isinstance(data, dict):
                    # Desencriptar campos sensibles si es necesario
                    decrypted_data = data.copy()
                    for field in SENSITIVE_FIELDS:
                        if field in decrypted_data and decrypted_data[field]:
                            # Si está encriptado, desencriptar; si no, dejar como está
                            decrypted = _decrypt_value_safe(decrypted_data[field])
                            if decrypted:
                                decrypted_data[field] = decrypted
                    update_from_api(decrypted_data)
        finally:
            db.close()
    except Exception:
        pass


def _load_notificaciones_envios() -> dict:
    """Carga la configuración de envíos de notificaciones desde la tabla configuracion (clave notificaciones_envios)."""
    try:
        from app.core.database import SessionLocal
        from app.models.configuracion import Configuracion
        db = SessionLocal()
        try:
            row = db.get(Configuracion, CLAVE_NOTIFICACIONES_ENVIOS)
            if row and row.valor:
                data = json.loads(row.valor)
                if isinstance(data, dict):
                    return data
        finally:
            db.close()
    except Exception:
        pass
    return {}


def init_from_settings() -> None:
    """Inicializa el holder desde settings (.env) para que el envío funcione sin pasar por la UI."""
    _current["smtp_host"] = getattr(settings, "SMTP_HOST", None) or ""
    _current["smtp_port"] = str(getattr(settings, "SMTP_PORT", None) or 587)
    _current["smtp_user"] = getattr(settings, "SMTP_USER", None) or ""
    _current["smtp_password"] = getattr(settings, "SMTP_PASSWORD", None) or ""
    _current["from_email"] = getattr(settings, "SMTP_FROM_EMAIL", None) or _current.get("smtp_user") or ""
    _current["from_name"] = "RapiCredit"
    _current["tickets_notify_emails"] = getattr(settings, "TICKETS_NOTIFY_EMAIL", None) or ""


def get_smtp_config() -> dict[str, Any]:
    """Devuelve la config SMTP actual (holder o settings)."""
    if _current.get("smtp_user"):
        return {
            "smtp_host": _current.get("smtp_host") or "",
            "smtp_port": int(_current.get("smtp_port") or 587),
            "smtp_user": _current.get("smtp_user") or "",
            "smtp_password": _current.get("smtp_password") or "",
            "from_email": _current.get("from_email") or _current.get("smtp_user") or "",
            "from_name": _current.get("from_name") or "RapiCredit",
        }
    return {
        "smtp_host": getattr(settings, "SMTP_HOST", None) or "",
        "smtp_port": getattr(settings, "SMTP_PORT", None) or 587,
        "smtp_user": getattr(settings, "SMTP_USER", None) or "",
        "smtp_password": getattr(settings, "SMTP_PASSWORD", None) or "",
        "from_email": getattr(settings, "SMTP_FROM_EMAIL", None) or getattr(settings, "SMTP_USER", None) or "",
        "from_name": "RapiCredit",
    }


def get_tickets_notify_emails() -> List[str]:
    """Lista de emails a los que notificar cuando se crea/actualiza un ticket (contactos prestablecidos)."""
    raw = _current.get("tickets_notify_emails") or getattr(settings, "TICKETS_NOTIFY_EMAIL", None) or ""
    return [e.strip() for e in raw.split(",") if e.strip()]


def update_from_api(data: dict[str, Any]) -> None:
    """Actualiza el holder desde la API de configuración (PUT /configuracion/email/configuracion)."""
    for k in ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name", "tickets_notify_emails", "modo_pruebas", "email_pruebas", "emails_pruebas"):
        if k in data and data[k] is not None:
            _current[k] = data[k]
    if "smtp_port" in data and data["smtp_port"] is not None:
        _current["smtp_port"] = str(data["smtp_port"])


def prepare_for_db_storage(data: dict[str, Any]) -> dict[str, Any]:
    """
    Prepara datos para guardar en BD: encripta campos sensibles.
    
    Args:
        data: Configuración a guardar
        
    Returns:
        Diccionario con campos sensibles encriptados (valores en valor_encriptado)
    """
    result = data.copy()
    
    # Para cada campo sensible, intentar encriptar
    for field in SENSITIVE_FIELDS:
        if field in result and result[field]:
            encrypted = _encrypt_value_safe(result[field])
            if encrypted:
                # Guardar el valor encriptado en el dict con sufijo _encriptado
                result[f"{field}_encriptado"] = encrypted.hex()  # Convertir bytes a hex string para JSON
                # Limpiar el valor original para no guardarlo en texto plano
                result[field] = None
    
    return result


def prepare_for_api_response(data: dict[str, Any]) -> dict[str, Any]:
    """
    Prepara datos para devolver a la API: enmascara campos sensibles.
    
    Args:
        data: Configuración almacenada en BD o caché
        
    Returns:
        Diccionario con campos sensibles enmascarados
    """
    result = data.copy()
    
    # Enmascarar campos sensibles
    for field in SENSITIVE_FIELDS:
        if field in result and result[field]:
            result[field] = _mask_sensitive_value(result[field])
    
    return result


def get_modo_pruebas_email() -> Tuple[bool, List[str]]:
    """
    Devuelve (modo_pruebas, list_of_emails).
    modo_pruebas True = redirigir todos los envíos al correo(s) de pruebas.
    list_of_emails = direcciones a las que enviar en modo pruebas (puede ser 1 o más).

    Prioridad:
    1. notificaciones_envios (clave en configuracion): si modo_pruebas=true y tiene emails_pruebas (array) o email_pruebas (string), usar esos.
    2. Fallback: email_config (email_pruebas como string único, convertido a lista de 1).
    """
    sync_from_db()

    # 1. Primero verificar notificaciones_envios (config de Notificaciones > Envíos)
    envios = _load_notificaciones_envios()
    raw_modo = envios.get("modo_pruebas") or _current.get("modo_pruebas") or getattr(settings, "MODO_PRUEBAS_EMAIL", None) or "false"
    modo = (str(raw_modo).lower() == "true" or raw_modo is True)

    if modo:
        emails: List[str] = []
        # emails_pruebas (array) tiene prioridad
        raw_emails = envios.get("emails_pruebas")
        if isinstance(raw_emails, list):
            emails = [e.strip() for e in raw_emails if e and isinstance(e, str) and e.strip() and "@" in e.strip()]
        # Si no hay array o está vacío, usar email_pruebas (legacy string)
        if not emails:
            raw_single = envios.get("email_pruebas") or _current.get("email_pruebas") or ""
            single = (raw_single or "").strip() if isinstance(raw_single, str) else ""
            if single and "@" in single:
                emails = [single]
        # Fallback: email_config (email_pruebas)
        if not emails:
            single = (_current.get("email_pruebas") or "").strip()
            if single and "@" in single:
                emails = [single]
        return (modo, emails)

    return (modo, [])
