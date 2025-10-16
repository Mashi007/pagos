"""
SOLUCIÓN DEFINITIVA PARA CORS
Middleware personalizado que garantiza CORS funcione correctamente
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import logging

logger = logging.getLogger(__name__)

class CORSFixMiddleware(BaseHTTPMiddleware):
    """
    Middleware CORS personalizado que garantiza headers correctos
    SOLUCIÓN DEFINITIVA - NO PARCHE TEMPORAL
    """
    
    def __init__(self, app, allowed_origins: list):
        super().__init__(app)
        self.allowed_origins = allowed_origins
        logger.info(f"🌐 CORSFixMiddleware inicializado con origins: {allowed_origins}")
    
    async def dispatch(self, request: Request, call_next):
        """
        Procesar request y agregar headers CORS
        """
        # Obtener origin del request
        origin = request.headers.get("origin")
        logger.info(f"🌐 Request origin: {origin}")
        
        # Crear response
        response = await call_next(request)
        
        # Agregar headers CORS
        if origin in self.allowed_origins:
            logger.info(f"✅ Origin permitido: {origin}")
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "86400"
        else:
            logger.warning(f"❌ Origin no permitido: {origin}")
            # Permitir localhost para desarrollo
            if origin and "localhost" in origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                response.headers["Access-Control-Allow-Headers"] = "*"
        
        # Manejar preflight requests
        if request.method == "OPTIONS":
            logger.info("🌐 Procesando OPTIONS preflight request")
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "86400"
            return StarletteResponse(status_code=200)
        
        logger.info(f"🌐 Headers CORS agregados para origin: {origin}")
        return response
