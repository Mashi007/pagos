#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de integración: Agrega las mejoras a main.py
Ejecutar desde: cd backend && python ../scripts_patches/integrate_improvements.py
"""

import os
import sys

BACKEND_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_PY_PATH = os.path.join(BACKEND_PATH, 'app', 'main.py')

def integrate_improvements():
    """Integra todas las mejoras en main.py"""
    
    print("=" * 70)
    print("INTEGRACIÓN DE MEJORAS EN main.py")
    print("=" * 70)
    
    # Leer archivo actual
    with open(MAIN_PY_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # CAMBIO 1: Agregar imports de encoding
    print("\n1. Agregando imports de encoding_config...")
    old_imports = """from app.services.liquidado_scheduler import liquidado_scheduler

# Configurar logging con UTF-8"""
    
    new_imports = """from app.services.liquidado_scheduler import liquidado_scheduler
from app.core.encoding_config import (
    configurar_fastapi_utf8,
    inicializar_encoding,
    UTF8EncodingMiddleware
)

# Configurar logging con UTF-8"""
    
    if old_imports in content:
        content = content.replace(old_imports, new_imports)
        print("   ✓ Imports agregados")
    else:
        print("   ⚠️ No se encontró la sección esperada (cambio manual requerido)")
    
    # CAMBIO 2: Agregar configuración UTF-8 después de crear app
    print("\n2. Agregando configuración UTF-8 en FastAPI...")
    old_app_creation = """# Crear aplicaciA3n FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

def _cors_headers_for_request(request: Request):"""
    
    new_app_creation = """# Crear aplicaciA3n FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ✅ NUEVO: Configurar UTF-8 PRIMERO (crítico para notificaciones)
configurar_fastapi_utf8(app)

def _cors_headers_for_request(request: Request):"""
    
    if old_app_creation in content:
        content = content.replace(old_app_creation, new_app_creation)
        print("   ✓ Configuración UTF-8 agregada")
    else:
        print("   ⚠️ No se encontró la sección esperada (cambio manual requerido)")
    
    # CAMBIO 3: Agregar middleware UTF8
    print("\n3. Agregando middleware UTF8...")
    old_middleware = """# Log de cada request (mActodo, ruta, status, tiempo) para depuraciA3n en Render
app.add_middleware(RequestLogMiddleware)

# Middleware: Validaci"""
    
    new_middleware = """# Log de cada request (mActodo, ruta, status, tiempo) para depuraciA3n en Render
app.add_middleware(RequestLogMiddleware)

# ✅ NUEVO: Middleware para UTF-8 en respuestas
app.add_middleware(UTF8EncodingMiddleware)

# Middleware: Validaci"""
    
    if old_middleware in content:
        content = content.replace(old_middleware, new_middleware)
        print("   ✓ Middleware UTF8 agregado")
    else:
        print("   ⚠️ No se encontró la sección esperada (cambio manual requerido)")
    
    # CAMBIO 4: Incluir nuevo router de tasas
    print("\n4. Agregando router de validación de tasas...")
    old_routers = """from app.api.v1.endpoints import admin_tasas_cambio
app.include_router(dashboard_conciliacion.router)
app.include_router(admin_tasas_cambio.router)


def _startup_db_with_retry"""
    
    new_routers = """from app.api.v1.endpoints import admin_tasas_cambio
from app.api.v1.endpoints import tasa_cambio_validacion
app.include_router(dashboard_conciliacion.router)
app.include_router(admin_tasas_cambio.router)
# ✅ NUEVO: Router de validación de tasas mejorado
app.include_router(tasa_cambio_validacion.router)


def _startup_db_with_retry"""
    
    if old_routers in content:
        content = content.replace(old_routers, new_routers)
        print("   ✓ Router de validación agregado")
    else:
        print("   ⚠️ No se encontró la sección esperada (cambio manual requerido)")
    
    # CAMBIO 5: Agregar startup event para encoding
    print("\n5. Agregando inicialización de encoding en startup...")
    old_startup = """@app.on_event("startup")
def on_startup():
    """Crear tablas en la BD si no existen. Inicializar config de email desde .env. Iniciar scheduler de reportes 
cobranzas."""
    from app.core.database import engine
    from app.core.email_config_holder import init_from_settings as init_email_config
    from app.core.scheduler import start_scheduler

    init_email_config()
    logger.info("ConfiguraciA3n de email (SMTP/tickets) inicializada desde variables de entorno.")"""
    
    new_startup = """@app.on_event("startup")
def on_startup():
    """Crear tablas en la BD si no existen. Inicializar config de email desde .env. Iniciar scheduler de reportes 
cobranzas."""
    from app.core.database import engine
    from app.core.email_config_holder import init_from_settings as init_email_config
    from app.core.scheduler import start_scheduler

    # ✅ NUEVO: Inicializar encoding UTF-8
    inicializar_encoding()
    logger.info("✓ Encoding UTF-8 configurado globalmente")

    init_email_config()
    logger.info("ConfiguraciA3n de email (SMTP/tickets) inicializada desde variables de entorno.")"""
    
    if old_startup in content:
        content = content.replace(old_startup, new_startup)
        print("   ✓ Inicialización de encoding agregada")
    else:
        print("   ⚠️ No se encontró la sección esperada (cambio manual requerido)")
    
    # Guardar archivo
    print("\n6. Guardando cambios en main.py...")
    with open(MAIN_PY_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("   ✓ Archivo guardado")
    
    print("\n" + "=" * 70)
    print("✅ INTEGRACIÓN COMPLETADA")
    print("=" * 70)
    print("\nÚltimos pasos:")
    print("1. Ejecutar: python backend/scripts/limpiar_emails.py")
    print("2. Testear en staging: GET /admin/tasas-cambio/validar-para-pago")
    print("3. Monitorear logs de la aplicación")
    print("\nDocumentación: IMPLEMENTACION_COMPLETADA_5_RIESGOS.md")


if __name__ == '__main__':
    try:
        integrate_improvements()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
