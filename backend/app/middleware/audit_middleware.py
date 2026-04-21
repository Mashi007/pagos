"""
Middleware de auditoria automatico.
Intercepta todos los POST/PUT/DELETE/PATCH y registra en tabla auditoria.

- Exito (2xx-3xx): exito=True, detalles con cuerpo enmascarado (sin passwords/tokens).
- Fallo (4xx-5xx): exito=False, mensaje_error con codigo HTTP y request_id si existe;
  mismo detalle enmascarado. Omitido en POST bajo /api/v1/pagos* con 409 (duplicados masivos).
"""
import json
import logging
from datetime import datetime
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.user import User
from app.models.auditoria import Auditoria
from app.middleware.audit_helpers import (
    audit_entity_from_path,
    format_http_error_message,
    redact_body_for_audit,
    skip_failed_audit_persist,
)

logger = logging.getLogger(__name__)

def _usuario_id_desde_bearer(request: Request, db) -> Optional[int]:
    auth = (request.headers.get("authorization") or "").strip()
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    payload = decode_token(token)
    if not payload or payload.get("type") != "access" or payload.get("scope") == "finiquito":
        return None
    sub = payload.get("sub") or payload.get("email")
    if not sub:
        return None
    email = str(sub).strip().lower()
    if "@" not in email:
        email = f"{email}@admin.local"
    u = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    return int(u.id) if u else None


def _resolve_usuario_id(request: Request, db) -> int:
    usuario_id = None
    try:
        usuario_info = getattr(request.state, "user", None)
        if usuario_info and hasattr(usuario_info, "id"):
            usuario_id = usuario_info.id
    except Exception:
        pass
    if not usuario_id:
        usuario_id = _usuario_id_desde_bearer(request, db)
    if not usuario_id:
        # Usuario de sistema para eventos sin sesión de personal (p.ej. endpoints públicos).
        usuario_id = 1
    return usuario_id


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
    safe_body = redact_body_for_audit(path, body_data)
    detalles = json.dumps(safe_body, default=str)[:500]
    client_ip = request.client.host if request.client else None
    ua = (request.headers.get("user-agent") or "")[:2000] or None

    db = SessionLocal()
    try:
        usuario_id = _resolve_usuario_id(request, db)
        db.add(
            Auditoria(
                usuario_id=usuario_id,
                accion=method,
                entidad=entidad,
                entidad_id=entidad_id,
                detalles=detalles,
                ip_address=client_ip,
                user_agent=ua,
                exito=exito,
                mensaje_error=(mensaje_error[:2000] if mensaje_error else None),
                fecha=datetime.now(),
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
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
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
