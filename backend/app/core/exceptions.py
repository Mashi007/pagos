"""
Manejo centralizado de excepciones
Proporciona clases de excepción personalizadas y manejo global
"""

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Excepción base de la aplicación"""

    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    """Excepción de validación"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, details=details)


class NotFoundException(AppException):
    """Recurso no encontrado"""

    def __init__(self, message: str = "Recurso no encontrado", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, details=details)


class DatabaseException(AppException):
    """Excepción de base de datos"""

    def __init__(self, message: str = "Error de base de datos", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details=details)


class AuthenticationException(AppException):
    """Excepción de autenticación"""

    def __init__(self, message: str = "Error de autenticación", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class AuthorizationException(AppException):
    """Excepción de autorización"""

    def __init__(self, message: str = "No tiene permisos para esta acción", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, details=details)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Manejador global de excepciones
    Captura todas las excepciones no manejadas y retorna respuestas apropiadas
    """
    request_id = getattr(request.state, "request_id", None)

    # Si es una excepción de la aplicación, usar su información
    if isinstance(exc, AppException):
        logger.warning(
            f"AppException: {exc.message}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "request_id": request_id,
                **({"details": exc.details} if exc.details else {}),
            },
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    # Si es HTTPException de FastAPI, preservarla pero agregar request_id
    if isinstance(exc, HTTPException):
        logger.warning(
            f"HTTPException: {exc.detail}",
            extra={"request_id": request_id, "status_code": exc.status_code, "path": request.url.path},
        )

        content = {"detail": exc.detail}
        if request_id:
            content["request_id"] = request_id

        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    # Excepción no esperada - manejar según ambiente
    import traceback

    error_traceback = traceback.format_exc()
    logger.error(
        f"❌ [GLOBAL EXCEPTION HANDLER] Unhandled exception: {type(exc).__name__}: {str(exc)}\n"
        f"Path: {request.url.path}\n"
        f"Method: {request.method}\n"
        f"Request ID: {request_id}\n"
        f"Traceback completo:\n{error_traceback}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    # Determinar mensaje de error según el tipo
    error_type = type(exc).__name__
    error_msg = str(exc)

    # Mensajes más descriptivos según el tipo de error
    if "ValidationError" in error_type or "Pydantic" in error_type:
        detail_msg = f"Error de validación: {error_msg[:200]}"
    elif "AttributeError" in error_type or "'NoneType' object" in error_msg:
        detail_msg = f"Error de datos: {error_msg[:200]}. Verifica que todos los campos requeridos estén presentes."
    elif "KeyError" in error_type:
        detail_msg = f"Error de estructura de datos: {error_msg[:200]}"
    elif "ValueError" in error_type:
        detail_msg = f"Error de validación: {error_msg[:200]}"
    elif "TypeError" in error_type:
        detail_msg = f"Error de tipo de dato: {error_msg[:200]}"
    elif "ImportError" in error_type or "ModuleNotFoundError" in error_type:
        detail_msg = f"Error de importación: {error_msg[:200]}. Verifica que todas las dependencias estén instaladas."
    else:
        detail_msg = f"Error interno ({error_type}): {error_msg[:300]}"

    # En producción, mostrar mensaje descriptivo pero no el traceback completo
    if settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": detail_msg,
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    # En desarrollo, mostrar más detalles incluyendo el tipo
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": detail_msg,
            "type": error_type,
            "full_error": error_msg,
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id} if request_id else {},
    )
