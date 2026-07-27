"""
Helpers para AuditMiddleware: redaccion de cuerpos y exclusion de auditoria ruidosa.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# Claves cuyo valor no debe persistirse en auditoria (login, tokens, secretos SMTP, etc.).
_SENSITIVE_KEY_LOWER = frozenset(
    {
        "password",
        "new_password",
        "confirm_password",
        "current_password",
        "refresh_token",
        "access_token",
        "token",
        "id_token",
        "secret",
        "client_secret",
        "smtp_password",
        "imap_password",
        "authorization",
        "otp",
        "codigo_otp",
    }
)


def is_auth_credential_path(path: str) -> bool:
    """Rutas donde el cuerpo suele llevar contrasena o tokens: no persistir JSON parseado."""
    p = path.lower()
    return (
        "/auth/login" in p
        or "/auth/refresh" in p
        or "forgot-password" in p
        or "/auth/forgot" in p
    )


def email_from_login_body(body_data: Any) -> Optional[str]:
    """Email del intento de login (sin password). Distintivo admin/operador."""
    if not isinstance(body_data, dict):
        return None
    raw = body_data.get("email") or body_data.get("username")
    if not raw:
        return None
    email = str(raw).strip().lower()
    if not email:
        return None
    if "@" not in email:
        email = f"{email}@admin.local"
    return email


def should_audit_request(path: str, *, has_staff_token: bool) -> bool:
    """
    Solo actividad de personal (Bearer) o login.
    Evita llenar auditoria con trafico publico anonimo como usuario_id=1.
    """
    p = (path or "").lower()
    if any(
        x in p
        for x in (
            "/health",
            "/openapi",
            "/docs",
            "/redoc",
            "/favicon",
            "/metrics",
        )
    ):
        return False
    if "/estado-cuenta/public" in p:
        return False
    if "/cobros/public" in p or "/cobros-publico" in p:
        return False
    if "/tasas-cambio/public" in p:
        return False
    if "/auth/login" in p:
        return True
    return bool(has_staff_token)


def auth_accion_label(path: str, method: str, *, exito: bool) -> str:
    """Etiquetas claras para auth; resto = metodo HTTP."""
    p = (path or "").lower()
    if "/auth/login" in p:
        return "LOGIN" if exito else "LOGIN_FAIL"
    if "/auth/logout" in p:
        return "LOGOUT"
    if "/auth/refresh" in p:
        return "REFRESH" if exito else "REFRESH_FAIL"
    return (method or "POST").upper()


def redact_body_for_audit(path: str, body_data: Any, max_depth: int = 6) -> Any:
    """
    Devuelve una copia segura para JSON en columna detalles.
    En rutas de credenciales: marcador + email (sin password).
    """
    if is_auth_credential_path(path):
        out: Dict[str, Any] = {"_redacted": "credentials"}
        em = email_from_login_body(body_data)
        if em:
            out["email"] = em
        return out

    if not isinstance(body_data, dict):
        return body_data

    def _walk(obj: Any, depth: int) -> Any:
        if depth > max_depth:
            return "[max_depth]"
        if isinstance(obj, dict):
            out: Dict[str, Any] = {}
            for k, v in obj.items():
                lk = str(k).lower()
                if lk in _SENSITIVE_KEY_LOWER or lk.endswith("_token"):
                    out[k] = "[REDACTED]"
                elif isinstance(v, dict):
                    out[k] = _walk(v, depth + 1)
                elif isinstance(v, list):
                    out[k] = [
                        _walk(i, depth + 1) if isinstance(i, (dict, list)) else i
                        for i in v[:50]
                    ]
                else:
                    out[k] = v
            return out
        if isinstance(obj, list):
            return [_walk(i, depth + 1) if isinstance(i, (dict, list)) else i for i in obj[:50]]
        return obj

    return _walk(body_data, 0)


def skip_failed_audit_persist(path: str, method: str, status_code: int) -> bool:
    """
    True = no insertar fila de auditoria para esta respuesta de error.
    Evita millones de filas en carga masiva de pagos duplicados (409).
    """
    if status_code != 409 or method.upper() != "POST":
        return False
    p = path.rstrip("/")
    # POST /api/v1/pagos (alta simple) o /api/v1/pagos/batch, /upload, etc. bajo pagos
    if re.search(r"/api/v1/pagos(?:/|$)", p):
        return True
    return False


def audit_entity_from_path(path: str) -> Tuple[str, Optional[int]]:
    """Misma heuristica que el middleware: entidad = penultimo segmento; id = primer entero al final."""
    segments = [s for s in path.split("/") if s]
    entidad = (
        segments[-2] if len(segments) >= 2 else (segments[-1] if segments else path)
    )
    m = re.search(r"/(\d+)(?:/|$)", path)
    entidad_id: Optional[int] = None
    if m:
        try:
            entidad_id = int(m.group(1))
        except (ValueError, OverflowError):
            pass
    return entidad, entidad_id


def format_http_error_message(status_code: int, response_headers: Any) -> str:
    rid = None
    if response_headers:
        rid = response_headers.get("X-Request-ID") or response_headers.get("X-Request-Id")
    msg = f"HTTP {status_code}"
    if rid:
        msg += f" request_id={rid}"
    return msg
