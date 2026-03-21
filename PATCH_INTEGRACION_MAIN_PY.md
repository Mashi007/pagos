# -*- coding: utf-8 -*-
"""
PATCH: Integración de mejoras críticas en main.py

Este patch agrega:
1. Configuración de encoding UTF-8 global
2. Middleware para garantizar UTF-8 en respuestas
3. Nuevos routers para validación de tasas y notificaciones mejoradas
4. Inicialización de servicios mejorados

Copia las líneas relevantes a tu main.py en los puntos indicados.
"""

# ============================================================================
# PASO 1: Agregar estos imports al inicio de main.py (después de imports existentes)
# ============================================================================

"""
from app.core.encoding_config import (
    configurar_fastapi_utf8,
    inicializar_encoding,
    UTF8EncodingMiddleware
)
"""

# ============================================================================
# PASO 2: Agregar esta configuración INMEDIATAMENTE DESPUÉS de crear app
# ============================================================================

"""
# Crear aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ✅ AGREGAR AQUÍ: Configurar UTF-8 PRIMERO (antes de otros middlewares)
configurar_fastapi_utf8(app)
"""

# ============================================================================
# PASO 3: Agregar startup event para inicializar encoding
# ============================================================================

"""
@app.on_event("startup")
async def startup_event():
    '''Inicializar servicios al startup de la aplicación'''
    inicializar_encoding()
    logger.info("✓ Encoding configurado a UTF-8")
    
    # Aquí van otros inits si los hay
"""

# ============================================================================
# PASO 4: Agregar middleware UTF8 DESPUÉS de otros middlewares
# ============================================================================

"""
# Agregar después de: app.add_middleware(RequestLogMiddleware)
app.add_middleware(UTF8EncodingMiddleware)
"""

# ============================================================================
# PASO 5: Incluir nuevos routers
# ============================================================================

"""
# Agregar después de: app.include_router(admin_tasas_cambio.router)

# Incluir router mejorado de validación de tasas de cambio
from app.api.v1.endpoints import tasa_cambio_validacion
app.include_router(tasa_cambio_validacion.router)

# Nota: Los routers de notificaciones ya están incluidos en api_router
# pero ahora tienen validación de email integrada
"""

# ============================================================================
# EJEMPLO: main.py modificado (estructura simplificada)
# ============================================================================

MAIN_PY_TEMPLATE = '''
"""
Aplicación principal FastAPI - MEJORADA CON UTF-8 Y VALIDACIONES
"""
import time
import logging
import warnings
from datetime import datetime

# ... imports existentes ...
from app.core.config import settings
from app.api.v1 import api_router
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.validador_sobre_aplicacion import ValidadorSobreAplicacionMiddleware
from app.services.liquidado_scheduler import liquidado_scheduler

# ✅ NUEVO: Imports para encoding y validaciones
from app.core.encoding_config import (
    configurar_fastapi_utf8,
    inicializar_encoding,
    UTF8EncodingMiddleware
)

# ... configuración de logging existente ...

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ✅ NUEVO: Configurar UTF-8 PRIMERO (crítico)
configurar_fastapi_utf8(app)

# ... exception handlers existentes ...

# Middlewares
app.add_middleware(RequestLogMiddleware)
app.add_middleware(UTF8EncodingMiddleware)  # ✅ NUEVO
app.add_middleware(ValidadorSobreAplicacionMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600,
)

# Routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(prestamos_liquidado_automatico.router)
app.include_router(conciliacion.router)
app.include_router(referencia_estados_cuota.router)
app.include_router(auditoria_conciliacion.router)
app.include_router(criticos.router)
app.include_router(dashboard_conciliacion.router)
app.include_router(admin_tasas_cambio.router)

# ✅ NUEVO: Incluir router de validación de tasas mejorado
from app.api.v1.endpoints import tasa_cambio_validacion
app.include_router(tasa_cambio_validacion.router)

# Startup events
@app.on_event("startup")
async def startup_event():
    """Inicializar servicios al startup"""
    
    # ✅ NUEVO: Configurar encoding
    inicializar_encoding()
    logger.info("✓ Encoding UTF-8 configurado")
    
    # ... otros inits existentes ...

# ... resto del código existente ...
'''

# ============================================================================
# CONFIGURACIÓN DE NOTIFICACIONES CON VALIDACIONES
# ============================================================================

"""
En notificaciones.py o notificaciones_tabs.py, agregar al inicio:

from app.utils.validators import es_email_valido
from app.utils.email_validators import validar_lote_emails

Y en las funciones de envío masivo:

@router.post("/enviar-todas-validado")
def enviar_todas_validado(db: Session = Depends(get_db)):
    clientes = db.query(Cliente).all()
    
    # Validar emails antes de envío
    stats = validar_lote_emails(clientes)
    logger.info(f"Validación: {stats['validos']} válidos, {stats['invalidos']} inválidos")
    
    # Solo enviar a clientes con email válido
    enviados = 0
    for cliente in clientes:
        es_valido, _ = validar_email_antes_envio(cliente.email, cliente.id)
        if es_valido:
            enviar_notificacion(cliente)
            enviados += 1
    
    return {"total": len(clientes), "procesados": enviados}
"""

# ============================================================================
# CONFIGURACIÓN DE TRANSACCIONES EN ENVÍO MASIVO
# ============================================================================

"""
En notificaciones.py, reemplazar enviar_todas() con:

from app.services.envio_masivo_transacciones import crear_envio_masivo_con_transaccion

@router.post("/enviar-todas-seguro")
def enviar_todas_seguro(db: Session = Depends(get_db)):
    '''Envío masivo con transacciones ACID'''
    
    clientes = db.query(Cliente).all()
    
    def enviar_a_cliente(cliente, db_session):
        try:
            # Validar email
            if not es_email_valido(cliente.email):
                logger.warning(f"Email inválido para {cliente.id}: {cliente.email}")
                return False
            
            # Enviar
            send_email(cliente.email, ...)
            
            # Registrar en BD (dentro de transacción)
            db_session.add(EnvioNotificacion(...))
            return True
        except Exception as e:
            logger.error(f"Error enviando a {cliente.id}: {e}")
            return False
    
    try:
        resultado = crear_envio_masivo_con_transaccion(
            db=db,
            clientes=clientes,
            enviar_func=enviar_a_cliente,
            tipo='notificacion_masiva'
        )
        return resultado
    except Exception as e:
        return {"error": str(e), "estado": "FALLÓ"}
"""

# ============================================================================
# CONFIGURACIÓN DE REINTENTOS DE EMAIL
# ============================================================================

"""
Para usar reintentos en servicios de email:

from app.services.email_service_reintentos import EmailServiceConReintentos

# Instanciar en startup o en config
email_service = EmailServiceConReintentos(
    smtp_host=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    username=settings.SMTP_USER,
    password=settings.SMTP_PASSWORD,
    max_reintentos=3
)

# Usar en lugar de send_email():
resultado = email_service.enviar_con_reintentos(
    destinatario=email,
    asunto=asunto,
    cuerpo=cuerpo,
    html=True
)

if resultado['exito']:
    logger.info(f"✓ Email enviado en intento {resultado['intento']}")
else:
    logger.error(f"✗ Error: {resultado['error']}")
"""

# ============================================================================
# CHECKLIST DE INTEGRACIÓN
# ============================================================================

CHECKLIST = """
✅ CHECKLIST DE INTEGRACIÓN

[ ] 1. Agregar imports de encoding_config en main.py
[ ] 2. Llamar configurar_fastapi_utf8(app) después de crear app
[ ] 3. Agregar @app.on_event("startup") con inicializar_encoding()
[ ] 4. Agregar app.add_middleware(UTF8EncodingMiddleware)
[ ] 5. Incluir router tasa_cambio_validacion
[ ] 6. Verificar que validators.py está en app/utils/
[ ] 7. Verificar que email_validators.py está en app/utils/
[ ] 8. Verificar que envio_masivo_transacciones.py está en app/services/
[ ] 9. Verificar que email_service_reintentos.py está en app/services/
[ ] 10. Ejecutar: python backend/scripts/limpiar_emails.py (sin confirmar primero)
[ ] 11. Testear en staging:
      - GET /admin/tasas-cambio/validar-para-pago → Debe retornar estado
      - POST /enviar-todas-validado → Debe validar emails
      - Enviar email → Debe reintentar si falla
      - Revisar que caracteres especiales (á, é, ñ) se ven bien
[ ] 12. Monitorear logs en producción
[ ] 13. Verificar métricas de email (rebotes, éxito, etc.)
[ ] 14. Celebrar las mejoras 🎉
"""

print(CHECKLIST)
