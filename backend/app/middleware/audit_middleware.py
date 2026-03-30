"""
Middleware de auditoria automatico.
Intercepta todos los POST/PUT/DELETE/PATCH y registra en tabla auditoria.
"""
import json
import logging
import re
from datetime import datetime
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.database import SessionLocal
from app.models.auditoria import Auditoria

logger = logging.getLogger(__name__)

_CACHED_FALLBACK_UID: Optional[int] = None


def _get_fallback_usuario_id(db) -> int:
    """
    Devuelve un usuario_id valido que exista en la tabla usuarios.
    Cachea el resultado en memoria para no consultar en cada request.
    """
    global _CACHED_FALLBACK_UID
    if _CACHED_FALLBACK_UID is not None:
        return _CACHED_FALLBACK_UID

    from sqlalchemy import text

    row = db.execute(
        text(
            "SELECT id FROM public.usuarios "
            "WHERE is_active = true ORDER BY id LIMIT 1"
        )
    ).first()
    uid = row[0] if row else 1
    _CACHED_FALLBACK_UID = uid
    return uid


def _extract_entidad_id(path: str) -> Optional[int]:
    """Extrae el ID numerico del path (ej. /api/v1/prestamos/123 -> 123)."""
    m = re.search(r"/(\d+)(?:/|$)", path)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, OverflowError):
            pass
    return None


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware que audita automaticamente todos los cambios (POST/PUT/DELETE/PATCH).
    Registra en tabla auditoria: usuario, accion, entidad, detalles, fecha.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
            return await call_next(request)

        body_bytes = await request.body()
        content_type = (request.headers.get("content-type") or "").lower()
        body_data = {}
        if body_bytes and "application/json" in content_type:
            try:
                body_data = json.loads(body_bytes.decode("utf-8", errors="replace"))
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

        if 200 <= response.status_code < 400:
            try:
                usuario_id = None
                try:
                    usuario_info = getattr(request.state, "user", None)
                    if usuario_info and hasattr(usuario_info, "id"):
                        usuario_id = usuario_info.id
                except Exception:
                    pass

                path = request.url.path
                method = request.method
                segments = [s for s in path.split("/") if s]
                entidad = segments[-2] if len(segments) >= 2 else (segments[-1] if segments else path)
                entidad_id = _extract_entidad_id(path)

                db = SessionLocal()
                try:
                    if not usuario_id:
                        usuario_id = _get_fallback_usuario_id(db)

                    audit_entry = Auditoria(
                        usuario_id=usuario_id,
                        accion=method,
                        entidad=entidad,
                        entidad_id=entidad_id,
                        detalles=json.dumps(body_data, default=str)[:500],
                        fecha=datetime.now(),
                    )
                    db.add(audit_entry)
                    db.commit()
                except Exception as e:
                    logger.warning("Error al registrar auditoria: %s", e)
                    db.rollback()
                finally:
                    db.close()
            except Exception as e:
                logger.exception("Error en AuditMiddleware: %s", e)

        return response
