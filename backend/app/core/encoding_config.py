# -*- coding: utf-8 -*-
"""
Configuración para fijar encoding UTF-8 en toda la aplicación.
Previene problemas con caracteres especiales en notificaciones.
"""

import sys
import io
from typing import Optional

# ============================================================================
# PASO 1: Configuración del intérprete Python para UTF-8
# ============================================================================

def configurar_encoding_global():
    """
    Configura el encoding global de Python a UTF-8.
    Llama al inicio de la aplicación.
    """
    
    # Para Python 3.7+
    if sys.version_info >= (3, 7):
        # Usar utf-8 mode (PEP 597)
        import os
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Asegurar que stdout y stderr usan UTF-8
    if sys.version_info[0] >= 3:
        try:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding='utf-8',
                errors='replace'
            )
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding='utf-8',
                errors='replace'
            )
        except (AttributeError, OSError):
            # Ya está configurado o hay error
            pass


# ============================================================================
# PASO 2: Middleware FastAPI para garantizar UTF-8 en respuestas
# ============================================================================

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class UTF8EncodingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que asegura todas las respuestas tengan charset UTF-8.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Asegurar que el header de content-type incluya charset=utf-8
        if 'content-type' in response.headers:
            content_type = response.headers['content-type']
            
            # Si no tiene charset, agregarlo
            if 'charset' not in content_type:
                if 'application/json' in content_type:
                    response.headers['content-type'] = f"{content_type}; charset=utf-8"
                elif 'text/' in content_type:
                    response.headers['content-type'] = f"{content_type}; charset=utf-8"
        
        # Agregar header explícito si no existe
        if 'charset' not in str(response.headers):
            response.headers['X-Content-Type-Options'] = 'nosniff'
        
        return response


# ============================================================================
# PASO 3: Configuración de FastAPI para JSONResponse UTF-8
# ============================================================================

def configurar_fastapi_utf8(app):
    """
    Configura una aplicación FastAPI para UTF-8.
    
    Uso en main.py:
    
        from fastapi import FastAPI
        app = FastAPI()
        
        # Configurar UTF-8
        configurar_fastapi_utf8(app)
        
        # ... resto de la app
    """
    
    # Agregar middleware
    app.add_middleware(UTF8EncodingMiddleware)
    
    # Sobrescribir JSONResponse por defecto
    from fastapi.responses import JSONResponse
    from fastapi.encoders import jsonable_encoder
    
    original_json_response = JSONResponse
    
    class UTF8JSONResponse(JSONResponse):
        def init_headers(self, headers=None):
            super().init_headers(headers)
            self.headers['charset'] = 'utf-8'
        
        def render(self, content):
            return super().render(jsonable_encoder(content))
    
    # Reemplazar
    app.default_response_class = UTF8JSONResponse


# ============================================================================
# PASO 4: Helpers para validar y limpiar strings UTF-8
# ============================================================================

def limpiar_utf8(texto: str) -> str:
    """
    Limpia un string para asegurar es valid UTF-8.
    Reemplaza caracteres inválidos.
    """
    if not isinstance(texto, str):
        return str(texto)
    
    # Codificar a UTF-8 y decodificar para limpiar
    try:
        return texto.encode('utf-8', errors='replace').decode('utf-8')
    except:
        return texto


def validar_utf8(texto: str) -> bool:
    """Valida que un string sea UTF-8 válido."""
    try:
        texto.encode('utf-8').decode('utf-8')
        return True
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False


# ============================================================================
# PASO 5: Decorador para funciones que retornan strings
# ============================================================================

def garantizar_utf8(func):
    """
    Decorador que garantiza que una función retorna strings UTF-8 válidos.
    
    Uso:
        @garantizar_utf8
        def obtener_nombre_cliente(id):
            # ... código
            return "María José García"  # ✓ Retorna correcto
    """
    
    def wrapper(*args, **kwargs):
        resultado = func(*args, **kwargs)
        
        if isinstance(resultado, str):
            return limpiar_utf8(resultado)
        elif isinstance(resultado, dict):
            return {k: limpiar_utf8(v) if isinstance(v, str) else v 
                    for k, v in resultado.items()}
        elif isinstance(resultado, list):
            return [limpiar_utf8(item) if isinstance(item, str) else item 
                    for item in resultado]
        
        return resultado
    
    return wrapper


# ============================================================================
# PASO 6: Inicialización (llamar en main.py al startup)
# ============================================================================

def inicializar_encoding():
    """
    Inicializa todas las configuraciones de encoding.
    Llamar al inicio de la aplicación.
    
    Uso en main.py:
    
        from app.core.encoding_config import inicializar_encoding
        
        @app.on_event("startup")
        async def startup():
            inicializar_encoding()
    """
    
    logger_local = __import__('logging').getLogger(__name__)
    
    logger_local.info("Configurando encoding global a UTF-8...")
    configurar_encoding_global()
    logger_local.info("✓ Encoding configurado")


# ============================================================================
# EJEMPLO DE USO COMPLETO
# ============================================================================

"""
# main.py

from fastapi import FastAPI
from app.core.encoding_config import (
    inicializar_encoding,
    configurar_fastapi_utf8
)

app = FastAPI(title="RapiCredit")

# Configurar UTF-8 PRIMERO
configurar_fastapi_utf8(app)

@app.on_event("startup")
async def startup():
    inicializar_encoding()

# ... resto de la app


# En un endpoint:

from app.core.encoding_config import garantizar_utf8

@router.get("/cliente/{cliente_id}")
@garantizar_utf8
def get_cliente(cliente_id: int):
    cliente = db.query(Cliente).get(cliente_id)
    return {
        "nombre": cliente.nombre,  # ✓ "María José" retorna bien
        "cedula": cliente.cedula
    }


# En un servicio:

from app.core.encoding_config import limpiar_utf8

def enviar_notificacion(cliente):
    nombre_limpio = limpiar_utf8(cliente.nombre)
    mensaje = f"Hola {nombre_limpio}, tu cuota vence..."
    send_email(cliente.email, "Recordatorio", mensaje)
"""
