"""
Formato unificado de errores HTTP para el API.
Todas las respuestas de error incluyen "detail" y "code" para que el frontend
pueda mostrar mensajes consistentes y opcionalmente tratar por código.
"""
from typing import Any

# Mapeo status_code -> código corto para el frontend
STATUS_TO_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def error_response_body(detail: Any, status_code: int) -> dict[str, Any]:
    """Construye el cuerpo JSON estándar de error: detail + code."""
    code = STATUS_TO_CODE.get(status_code, "ERROR")
    return {"detail": detail, "code": code}
