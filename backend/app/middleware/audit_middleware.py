"""
Middleware de auditoría automático.
Intercepta todos los POST/PUT/DELETE/PATCH y registra en tabla auditoria.
"""
import json
import logging
from datetime import datetime
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.database import SessionLocal
from app.models.auditoria import Auditoria
from app.core.deps import get_current_user

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware que audita automáticamente todos los cambios (POST/PUT/DELETE/PATCH).
    Registra en tabla auditoria: usuario, acción, entidad, detalles, fecha.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Solo auditar cambios, no GETs ni HEAD ni OPTIONS
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
            return await call_next(request)

        # Capturar payload (body)
        body_bytes = await request.body()
        try:
            body_data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            body_data = {}

        # Guardar body en request para que call_next pueda usarlo
        async def receive():
            return {"type": "http.request", "body": body_bytes}

        request._receive = receive

        # Ejecutar endpoint
        response: Response = await call_next(request)

        # Solo auditar si fue exitoso (2xx, 3xx)
        if 200 <= response.status_code < 400:
            try:
                # Extraer usuario (si está autenticado)
                usuario_id = None
                try:
                    # Intentar obtener usuario del JWT (request.state si fue inyectado)
                    usuario_info = getattr(request.state, "user", None)
                    if usuario_info and hasattr(usuario_info, "id"):
                        usuario_id = usuario_info.id
                except Exception:
                    pass

                # Fallback a usuario admin (1)
                if not usuario_id:
                    usuario_id = 1

                # Extraer detalles
                path = request.url.path
                method = request.method
                entidad = path.split("/")[-2] if "/" in path else path

                # Crear entrada en auditoría
                db = SessionLocal()
                try:
                    audit_entry = Auditoria(
                        usuario_id=usuario_id,
                        accion=f"{method}",
                        entidad=entidad,
                        entidad_id=None,  # Podría extraerse del path (/pagos/123 → 123)
                        detalles=json.dumps(body_data)[:500],  # Limitar a 500 chars
                        fecha=datetime.now(),
                    )
                    db.add(audit_entry)
                    db.commit()
                except Exception as e:
                    logger.warning(f"Error al registrar auditoría: {e}")
                    db.rollback()
                finally:
                    db.close()
            except Exception as e:
                # No romper la respuesta si la auditoría falla
                logger.exception(f"Error en AuditMiddleware: {e}")

        return response
