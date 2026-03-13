"""
Holder de configuraci�n de email en tiempo de ejecuci�n.
Usado por core/email.py para enviar (SMTP) y por tickets para destinos de notificaci�n.
La API configuracion/email actualiza este holder al guardar; si no se ha guardado, se usan settings (.env).
Para que Notificaciones/CRM usen la config guardada en BD, sync_from_db() carga desde la tabla configuracion antes de enviar.

Integraci�n con encriptaci�n:
- Campos sensibles (smtp_password, etc.) se encriptan al guardar en BD
- Se desencriptan autom�ticamente al cargar desde BD
- Al devolver al API, se enmascaran (no se expone la contrase�a)
"""
import json
import logging
import time
from typing import Any, List, Optional, Tuple

from app.core.config import settings
from app.core.email_phases import FASE_CONFIG_CARGA, log_phase

# Config actual: smtp_*, from_email, from_name, tickets_notify_emails (str, emails separados por coma)
_current: dict[str, Any] = {}

logger = logging.getLogger(__name__)

CLAVE_EMAIL_CONFIG = "email_config"
CLAVE_NOTIFICACIONES_ENVIOS = "notificaciones_envios"

# Campos sensibles que deben encriptarse en BD
SENSITIVE_FIELDS = {"smtp_password", "imap_password"}


def _mask_sensitive_value(value: Any) -> str:
    """Enmascara un valor sensible para devolver a la API (no exponer contrase�a)."""
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
        # Si desencriptaci�n falla, devolver None (posiblemente no estaba encriptado)
        return None
    return None


def _encrypt_value_safe(value: str, field_name: str) -> Optional[bytes]:
    """Intenta encriptar un valor; devuelve None si falla (ej. ENCRYPTION_KEY no definido)."""
    if not value or not _should_encrypt_field(field_name):
        return None
    try:
        from app.core.crypto import encrypt_value
        return encrypt_value(value)
    except Exception:
        return None


def sync_from_db() -> None:
    """Carga la configuraci�n de email desde la tabla configuracion y actualiza el holder. As� Notificaciones/CRM usan la config guardada en Configuraci�n > Email."""
    t0 = time.time()
    try:
        from app.core.database import SessionLocal
        from app.models.configuracion import Configuracion
        db = SessionLocal()
        try:
            row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
            if row and row.valor:
                data = json.loads(row.valor)
                if isinstance(data, dict):
                    decrypted_data = data.copy()
                    for field in SENSITIVE_FIELDS:
                        enc_key = f"{field}_encriptado"
                        if enc_key in data and data[enc_key]:
                            raw = data[enc_key]
                            enc_bytes = bytes.fromhex(raw) if isinstance(raw, str) else raw
                            decrypted = _decrypt_value_safe(enc_bytes)
                            decrypted_data[field] = decrypted if decrypted else data.get(field)
                        elif field in data and data[field] is not None:
                            decrypted_data[field] = data[field]
                    update_from_api(decrypted_data)
            log_phase(logger, FASE_CONFIG_CARGA, True, "config cargada desde BD", duration_ms=(time.time() - t0) * 1000)
        finally:
            db.close()
    except Exception as e:
        log_phase(logger, FASE_CONFIG_CARGA, False, str(e), duration_ms=(time.time() - t0) * 1000)
        logger.debug("sync_from_db fallo (se usara config en memoria/.env): %s", e)


def _load_notificaciones_envios() -> dict:
    """Carga la configuraci�n de env�os de notificaciones desde la tabla configuracion (clave notificaciones_envios)."""
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
    """Inicializa el holder desde settings (.env) para que el env�o funcione sin pasar por la UI."""
    _current["smtp_host"] = getattr(settings, "SMTP_HOST", None) or ""
    _current["smtp_port"] = str(getattr(settings, "SMTP_PORT", None) or 587)
    _current["smtp_user"] = getattr(settings, "SMTP_USER", None) or ""
    _current["smtp_password"] = getattr(settings, "SMTP_PASSWORD", None) or ""
    _current["from_email"] = getattr(settings, "SMTP_FROM_EMAIL", None) or _current.get("smtp_user") or ""
    _current["from_name"] = "RapiCredit"
    _current["tickets_notify_emails"] = getattr(settings, "TICKETS_NOTIFY_EMAIL", None) or ""


def get_smtp_config() -> dict[str, Any]:
    """Devuelve la config SMTP actual. Siempre carga desde BD primero para usar el correo guardado en Configuraci�n > Email (no el de .env)."""
    sync_from_db()
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



# Servicios que envian email: flag email_activo_<servicio> y modo_pruebas_<servicio>
EMAIL_SERVICES = ("notificaciones", "informe_pagos", "estado_cuenta", "cobros", "campanas", "tickets")
MODO_PRUEBAS_SERVICES = tuple("modo_pruebas_" + s for s in EMAIL_SERVICES)

def get_email_activo() -> bool:
    """Master: si False, ningun servicio envia email."""
    sync_from_db()
    v = _current.get("email_activo") or getattr(settings, "EMAIL_ACTIVO", None) or "true"
    return (str(v).lower() == "true" or v is True)

def get_email_activo_servicio(servicio: str) -> bool:
    """True si el servicio puede enviar email."""
    if not get_email_activo():
        return False
    key = "email_activo_" + servicio
    if key not in _current or _current[key] is None:
        return True
    return (str(_current[key]).lower() == "true" or _current[key] is True)

def update_from_api(data: dict[str, Any]) -> None:
    """Actualiza el holder desde la API de configuraci�n (PUT /configuracion/email/configuracion)."""
    keys = (
        "smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name",
        "tickets_notify_emails", "modo_pruebas", "email_pruebas", "emails_pruebas", "email_activo",
        "email_activo_notificaciones", "email_activo_informe_pagos", "email_activo_estado_cuenta",
        "email_activo_cobros", "email_activo_campanas", "email_activo_tickets",
        "modo_pruebas_notificaciones", "modo_pruebas_informe_pagos", "modo_pruebas_estado_cuenta",
        "modo_pruebas_cobros", "modo_pruebas_campanas", "modo_pruebas_tickets",
        "imap_host", "imap_port", "imap_user", "imap_password", "imap_use_ssl",
    )
    for k in keys:
        if k in data and data[k] is not None:
            _current[k] = data[k]
    if "smtp_port" in data and data["smtp_port"] is not None:
        _current["smtp_port"] = str(data["smtp_port"])


def prepare_for_db_storage(data: dict[str, Any]) -> dict[str, Any]:
    """
    Prepara datos para guardar en BD: encripta campos sensibles.
    
    Args:
        data: Configuraci�n a guardar
        
    Returns:
        Diccionario con campos sensibles encriptados (valores en valor_encriptado)
    """
    result = data.copy()
    
    # Para cada campo sensible, intentar encriptar
    for field in SENSITIVE_FIELDS:
        if field in result and result[field]:
            encrypted = _encrypt_value_safe(result[field], field)
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
        data: Configuraci�n almacenada en BD o cach�
        
    Returns:
        Diccionario con campos sensibles enmascarados
    """
    result = data.copy()
    
    # Enmascarar campos sensibles
    for field in SENSITIVE_FIELDS:
        if field in result and result[field]:
            result[field] = _mask_sensitive_value(result[field])
    
    return result


def get_modo_pruebas_email(servicio: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Devuelve (modo_pruebas, list_of_emails).
    modo_pruebas True = redirigir todos los env�os al correo(s) de pruebas.
    list_of_emails = direcciones a las que enviar en modo pruebas (puede ser 1 o m�s).

    Prioridad:
    1. notificaciones_envios (clave en configuracion): si modo_pruebas=true y tiene emails_pruebas (array) o email_pruebas (string), usar esos.
    2. Fallback: email_config (email_pruebas como string �nico, convertido a lista de 1).
    """
    sync_from_db()
    if servicio:
        use_modo = get_modo_pruebas_servicio(servicio)
        if not use_modo:
            return (False, [])
        return (True, _get_emails_pruebas_list())
    # Modo global (legacy)
    envios = _load_notificaciones_envios()
    raw_modo = envios.get("modo_pruebas") or _current.get("modo_pruebas") or getattr(settings, "MODO_PRUEBAS_EMAIL", None) or "false"
    modo = (str(raw_modo).lower() == "true" or raw_modo is True)
    if modo:
        return (modo, _get_emails_pruebas_list())
    return (modo, [])

    return (modo, [])


def get_modo_pruebas_servicio(servicio: str) -> bool:
    """True si este servicio debe redirigir envios al correo de pruebas."""
    sync_from_db()
    envios = _load_notificaciones_envios()
    # Para notificaciones: priorizar el toggle de Configuración > Notificaciones > Envíos (notificaciones_envios)
    # sobre modo_pruebas_notificaciones del tab Email, para que el batch use el valor que el usuario acaba de guardar.
    if servicio == "notificaciones":
        raw = envios.get("modo_pruebas")
        if raw is not None:
            if raw is True or (isinstance(raw, str) and raw.lower() == "true"):
                return True
            return False
    key = "modo_pruebas_" + servicio
    if key in _current and _current[key] is not None:
        v = _current[key]
        return (str(v).lower() == "true" or v is True)
    raw = envios.get("modo_pruebas") or _current.get("modo_pruebas") or getattr(settings, "MODO_PRUEBAS_EMAIL", None) or "false"
    return (str(raw).lower() == "true" or raw is True)


def _get_emails_pruebas_list() -> List[str]:
    """Lista de correos de pruebas (desde notificaciones_envios o email_config)."""
    envios = _load_notificaciones_envios()
    emails: List[str] = []
    raw_emails = envios.get("emails_pruebas")
    if isinstance(raw_emails, list):
        emails = [e.strip() for e in raw_emails if e and isinstance(e, str) and e.strip() and "@" in e.strip()]
    if not emails:
        raw_single = envios.get("email_pruebas") or _current.get("email_pruebas") or ""
        single = (raw_single or "").strip() if isinstance(raw_single, str) else ""
        if single and "@" in single:
            emails = [single]
    if not emails:
        single = (_current.get("email_pruebas") or "").strip()
        if single and "@" in single:
            emails = [single]
    return emails

