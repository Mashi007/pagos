"""
Middleware de auditoria automatico.
Intercepta POST/PUT/DELETE/PATCH de personal (admin/operador) y login; registra en auditoria con email como distintivo.

- Exito (2xx-3xx): exito=True, detalles con cuerpo enmascarado (sin passwords/tokens).
- Fallo (4xx-5xx): exito=False, mensaje_error con codigo HTTP y request_id si existe;
  mismo detalle enmascarado. Omitido en POST bajo /api/v1/pagos* con 409 (duplicados masivos).
"""
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import Request
from sqlalchemy import func
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.user import User
from app.models.auditoria import Auditoria
from app.middleware.audit_helpers import (
    audit_entity_from_path,
    auth_accion_label,
    email_from_login_body,
    format_http_error_message,
    redact_body_for_audit,
    should_audit_request,
    skip_failed_audit_persist,
)

logger = logging.getLogger(__name__)

def _usuario_desde_bearer(request: Request, db) -> tuple[Optional[int], Optional[str]]:
    """Resuelve (usuario_id, email) de personal desde JWT Bearer."""
    auth = (request.headers.get("authorization") or "").strip()
    if not auth.lower().startswith("bearer "):
        return None, None
    token = auth[7:].strip()
    payload = decode_token(token)
    if not payload or payload.get("type") != "access" or payload.get("scope") == "finiquito":
        return None, None
    email_claim = payload.get("email") or payload.get("sub")
    if not email_claim:
        return None, None
    raw = str(email_claim).strip()
    # sub numerico (id de usuarios)
    if raw.isdigit():
        u = (
            db.query(User)
            .filter(User.id == int(raw), User.is_active.is_(True))
            .first()
        )
        if u:
            return int(u.id), (str(u.email).lower() if u.email else None)
        return None, None
    email = raw.lower()
    if "@" not in email:
        email = f"{email}@admin.local"
    u = (
        db.query(User)
        .filter(func.lower(User.email) == email, User.is_active.is_(True))
        .first()
    )
    if u:
        return int(u.id), email
    # Token valido con email pero sin fila: conservar email para la UI (admin env, etc.)
    return None, email


def _resolve_usuario(request: Request, db) -> tuple[int, Optional[str]]:
    """Prioriza Bearer (admin/operador). Evita depender de request.state (BaseHTTPMiddleware)."""
    uid_bearer, email_bearer = _usuario_desde_bearer(request, db)
    if uid_bearer:
        return uid_bearer, email_bearer
    try:
        usuario_info = getattr(request.state, "user", None)
        if usuario_info and hasattr(usuario_info, "id"):
            uid = getattr(usuario_info, "id", None)
            email = getattr(usuario_info, "email", None)
            if uid is not None:
                return int(uid), (str(email).lower() if email else email_bearer)
    except Exception:
        pass
    if email_bearer:
        # Hay email de token pero no id en BD: registrar bajo 1 y denormalizar email
        logger.info(
            "Auditoria: token con email %s sin usuario BD; se registra email en detalles",
            email_bearer,
        )
        return 1, email_bearer
    logger.warning("Auditoria: sin sesion de personal; fallback usuario_id=1")
    return 1, None


def _persist_auditoria_row(
    *,
    request: Request,
    path: str,
    method: str,
    body_data: dict,
    exito: bool,
    mensaje_error: Optional[str],
) -> None:
    entidad, entidad_id = audit_entity_from_path(path)
    # Auth: entidad clara
    pl = (path or "").lower()
    if "/auth/" in pl:
        entidad = "auth"
    safe_body = redact_body_for_audit(path, body_data)
    if not isinstance(safe_body, dict):
        safe_body = {"_body": safe_body}
    client_ip = request.client.host if request.client else None
    ua = (request.headers.get("user-agent") or "")[:2000] or None
    accion = auth_accion_label(path, method, exito=exito)

    db = SessionLocal()
    try:
        usuario_id, usuario_email = _resolve_usuario(request, db)
        # Login no trae Bearer: email del body es el distintivo
        login_email = email_from_login_body(body_data) if "/auth/login" in pl else None
        if login_email:
            usuario_email = login_email
            u = (
                db.query(User)
                .filter(func.lower(User.email) == login_email)
                .first()
            )
            if u:
                usuario_id = int(u.id)
        if not usuario_email:
            # Ultimo recurso: no dejar actividad staff sin correo visible
            logger.warning(
                "Auditoria sin email (path=%s accion=%s usuario_id=%s)",
                path,
                accion,
                usuario_id,
            )
        detalles_obj: dict = {"_usuario_email": usuario_email} if usuario_email else {}
        detalles_obj.update(safe_body)
        if usuario_email:
            detalles_obj["_usuario_email"] = usuario_email
        detalles = json.dumps(detalles_obj, default=str)[:500]
        db.add(
            Auditoria(
                usuario_id=usuario_id,
                accion=accion,
                entidad=entidad,
                entidad_id=entidad_id,
                detalles=detalles,
                ip_address=client_ip,
                user_agent=ua,
                exito=exito,
                mensaje_error=(mensaje_error[:2000] if mensaje_error else None),
                fecha=datetime.now(timezone.utc),
            )
        )
        db.commit()
    except Exception as e:
        logger.warning("Error al registrar auditoria: %s", e)
        db.rollback()
    finally:
        db.close()


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware que audita automaticamente todos los cambios (POST/PUT/DELETE/PATCH).
    Registra en tabla auditoria: usuario, accion, entidad, detalles, fecha, exito, mensaje_error.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Actividad de admin/operador: mutaciones HTTP (+ login sin Bearer).
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
            return await call_next(request)

        path_pre = request.url.path or ""
        auth_hdr = (request.headers.get("authorization") or "").strip()
        has_staff_token = auth_hdr.lower().startswith("bearer ")
        if not should_audit_request(path_pre, has_staff_token=has_staff_token):
            return await call_next(request)

        body_bytes = await request.body()
        content_type = (request.headers.get("content-type") or "").lower()
        body_data: dict = {}
        if body_bytes and "application/json" in content_type:
            try:
                body_data = json.loads(body_bytes.decode("utf-8", errors="replace"))
                if not isinstance(body_data, dict):
                    body_data = {"_body": body_data}
            except (json.JSONDecodeError, ValueError):
                body_data = {}
        elif body_bytes and (
            "multipart" in content_type or "application/octet-stream" in content_type
        ):
            body_data = {"_body": "[multipart/binary - no parseado]"}

        async def receive():
            return {"type": "http.request", "body": body_bytes}

        request._receive = receive

        response: Response = await call_next(request)

        path = request.url.path
        method = request.method
        status = response.status_code

        try:
            if 200 <= status < 400:
                _persist_auditoria_row(
                    request=request,
                    path=path,
                    method=method,
                    body_data=body_data,
                    exito=True,
                    mensaje_error=None,
                )
            elif status >= 400:
                if skip_failed_audit_persist(path, method, status):
                    return response
                msg = format_http_error_message(status, response.headers)
                _persist_auditoria_row(
                    request=request,
                    path=path,
                    method=method,
                    body_data=body_data,
                    exito=False,
                    mensaje_error=msg,
                )
        except Exception as e:
            logger.exception("Error en AuditMiddleware: %s", e)

        return response
