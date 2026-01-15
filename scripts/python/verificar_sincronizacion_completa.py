#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que Frontend, Backend y Base de Datos estén sincronizados

Verifica:
1. Frontend - Endpoint correcto y configuración
2. Backend - Endpoint registrado e implementado
3. Base de Datos - Índices y extensiones instaladas
"""

import sys
import io
import os
from pathlib import Path
from datetime import datetime

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar backend al path para imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db.session import SessionLocal

def verificar_frontend():
    """Verifica que el frontend esté usando el endpoint correcto"""
    print("\n" + "=" * 70)
    print("1. VERIFICACIÓN DEL FRONTEND")
    print("=" * 70)
    
    resultados = {}
    
    # Verificar archivo ChatAI.tsx
    chat_ai_path = project_root / "frontend" / "src" / "pages" / "ChatAI.tsx"
    if chat_ai_path.exists():
        contenido = chat_ai_path.read_text(encoding='utf-8')
        
        # Verificar endpoint correcto
        endpoint_correcto = '/api/v1/configuracion/ai/chat'
        if endpoint_correcto in contenido:
            resultados["endpoint"] = True
            print(f"✅ Endpoint correcto: {endpoint_correcto}")
        else:
            resultados["endpoint"] = False
            print(f"❌ Endpoint NO encontrado: {endpoint_correcto}")
        
        # Verificar manejo de errores
        if 'timeout' in contenido.lower() and 'error' in contenido.lower():
            resultados["manejo_errores"] = True
            print("✅ Manejo de errores implementado")
        else:
            resultados["manejo_errores"] = False
            print("⚠️ Manejo de errores básico")
        
        # Verificar verificación de configuración AI
        if 'verificarConfiguracionAI' in contenido:
            resultados["verificacion_config"] = True
            print("✅ Verificación de configuración AI implementada")
        else:
            resultados["verificacion_config"] = False
            print("⚠️ Verificación de configuración AI no encontrada")
    else:
        print(f"❌ Archivo ChatAI.tsx no encontrado: {chat_ai_path}")
        resultados["endpoint"] = False
        resultados["manejo_errores"] = False
        resultados["verificacion_config"] = False
    
    # Verificar ruta en App.tsx
    app_tsx_path = project_root / "frontend" / "src" / "App.tsx"
    if app_tsx_path.exists():
        contenido_app = app_tsx_path.read_text(encoding='utf-8')
        if 'chat-ai' in contenido_app.lower():
            resultados["ruta_registrada"] = True
            print("✅ Ruta '/chat-ai' registrada en App.tsx")
        else:
            resultados["ruta_registrada"] = False
            print("❌ Ruta '/chat-ai' NO registrada en App.tsx")
    else:
        resultados["ruta_registrada"] = False
        print("❌ Archivo App.tsx no encontrado")
    
    # Verificar Sidebar
    sidebar_path = project_root / "frontend" / "src" / "components" / "layout" / "Sidebar.tsx"
    if sidebar_path.exists():
        contenido_sidebar = sidebar_path.read_text(encoding='utf-8')
        if '/chat-ai' in contenido_sidebar:
            resultados["sidebar"] = True
            print("✅ Enlace en Sidebar encontrado")
        else:
            resultados["sidebar"] = False
            print("⚠️ Enlace en Sidebar no encontrado")
    else:
        resultados["sidebar"] = False
    
    return resultados

def verificar_backend():
    """Verifica que el backend tenga el endpoint implementado y registrado"""
    print("\n" + "=" * 70)
    print("2. VERIFICACIÓN DEL BACKEND")
    print("=" * 70)
    
    resultados = {}
    
    # Verificar endpoint en configuracion.py
    config_path = project_root / "backend" / "app" / "api" / "v1" / "endpoints" / "configuracion.py"
    if config_path.exists():
        contenido = config_path.read_text(encoding='utf-8')
        
        # Verificar decorador del endpoint
        if '@router.post("/ai/chat")' in contenido or '@router.post("/ai/chat")' in contenido:
            resultados["endpoint_definido"] = True
            print("✅ Endpoint '/ai/chat' definido en configuracion.py")
        else:
            resultados["endpoint_definido"] = False
            print("❌ Endpoint '/ai/chat' NO encontrado en configuracion.py")
        
        # Verificar rate limiting
        if '@limiter.limit' in contenido and '20/minute' in contenido:
            resultados["rate_limiting"] = True
            print("✅ Rate limiting configurado (20/minute)")
        else:
            resultados["rate_limiting"] = False
            print("⚠️ Rate limiting no encontrado o incorrecto")
        
        # Verificar AIChatService
        if 'AIChatService' in contenido:
            resultados["servicio"] = True
            print("✅ AIChatService importado y usado")
        else:
            resultados["servicio"] = False
            print("❌ AIChatService no encontrado")
        
        # Verificar manejo de métricas
        if 'AIChatMetrics' in contenido:
            resultados["metricas"] = True
            print("✅ Sistema de métricas implementado")
        else:
            resultados["metricas"] = False
            print("⚠️ Sistema de métricas no encontrado")
    else:
        print("❌ Archivo configuracion.py no encontrado")
        resultados["endpoint_definido"] = False
        resultados["rate_limiting"] = False
        resultados["servicio"] = False
        resultados["metricas"] = False
    
    # Verificar registro en main.py
    main_path = project_root / "backend" / "app" / "main.py"
    if main_path.exists():
        contenido_main = main_path.read_text(encoding='utf-8')
        
        if 'configuracion.router' in contenido_main:
            resultados["router_registrado"] = True
            print("✅ Router de configuración registrado en main.py")
        else:
            resultados["router_registrado"] = False
            print("❌ Router de configuración NO registrado en main.py")
        
        # Verificar prefix correcto
        if 'prefix="/api/v1/configuracion"' in contenido_main:
            resultados["prefix_correcto"] = True
            print("✅ Prefix correcto: /api/v1/configuracion")
        else:
            resultados["prefix_correcto"] = False
            print("⚠️ Prefix puede estar incorrecto")
    else:
        resultados["router_registrado"] = False
        resultados["prefix_correcto"] = False
        print("❌ Archivo main.py no encontrado")
    
    # Verificar servicio AIChatService existe
    service_path = project_root / "backend" / "app" / "services" / "ai_chat_service.py"
    if service_path.exists():
        resultados["archivo_servicio"] = True
        print("✅ Archivo ai_chat_service.py existe")
    else:
        resultados["archivo_servicio"] = False
        print("❌ Archivo ai_chat_service.py NO existe")
    
    return resultados

def verificar_base_datos():
    """Verifica que la base de datos tenga índices y extensiones instaladas"""
    print("\n" + "=" * 70)
    print("3. VERIFICACIÓN DE BASE DE DATOS")
    print("=" * 70)
    
    db = SessionLocal()
    resultados = {}
    
    try:
        # Verificar extensión pg_trgm
        try:
            query = text("""
                SELECT extname, extversion
                FROM pg_extension
                WHERE extname = 'pg_trgm'
            """)
            resultado = db.execute(query)
            row = resultado.fetchone()
            
            if row:
                resultados["extension_pg_trgm"] = True
                print(f"✅ Extensión pg_trgm instalada (versión {row[1]})")
            else:
                resultados["extension_pg_trgm"] = False
                print("❌ Extensión pg_trgm NO instalada")
        except Exception as e:
            resultados["extension_pg_trgm"] = False
            print(f"❌ Error verificando extensión: {e}")
        
        # Verificar índices críticos
        indices_esperados = [
            "idx_cuotas_extract_year_month_vencimiento",
            "idx_prestamos_extract_year_month_registro",
            "idx_pagos_extract_year_month",
            "idx_cuotas_prestamo_estado_fecha_vencimiento",
            "idx_prestamos_estado_analista_cedula",
            "idx_pagos_fecha_activo_prestamo",
            "idx_prestamos_analista_trgm",
        ]
        
        try:
            query = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = ANY(:indices)
            """)
            resultado = db.execute(query, {"indices": indices_esperados})
            indices_encontrados = [row[0] for row in resultado.fetchall()]
            
            indices_faltantes = [idx for idx in indices_esperados if idx not in indices_encontrados]
            
            if not indices_faltantes:
                resultados["indices"] = True
                print(f"✅ Todos los índices creados ({len(indices_esperados)})")
            else:
                resultados["indices"] = False
                print(f"❌ Índices faltantes: {len(indices_faltantes)}")
                for idx in indices_faltantes:
                    print(f"   - {idx}")
        except Exception as e:
            resultados["indices"] = False
            print(f"❌ Error verificando índices: {e}")
        
        # Verificar configuración AI en BD
        try:
            from app.models.configuracion_sistema import ConfiguracionSistema
            configs = db.query(ConfiguracionSistema).filter(
                ConfiguracionSistema.categoria == "AI"
            ).all()
            
            if configs:
                config_dict = {config.clave: config.valor for config in configs}
                activo = config_dict.get("activo", "").lower() == "true"
                
                resultados["config_ai"] = True
                resultados["ai_activo"] = activo
                print(f"✅ Configuración AI encontrada ({len(configs)} parámetros)")
                print(f"   Estado: {'ACTIVO' if activo else 'INACTIVO'}")
            else:
                resultados["config_ai"] = False
                resultados["ai_activo"] = False
                print("❌ Configuración AI NO encontrada en BD")
        except Exception as e:
            resultados["config_ai"] = False
            resultados["ai_activo"] = False
            print(f"❌ Error verificando configuración AI: {e}")
        
        # Verificar conexión a tablas principales
        try:
            from app.models.cliente import Cliente
            from app.models.prestamo import Prestamo
            from app.models.pago import Pago
            from app.models.amortizacion import Cuota
            
            total_clientes = db.query(Cliente).count()
            total_prestamos = db.query(Prestamo).count()
            total_pagos = db.query(Pago).count()
            total_cuotas = db.query(Cuota).count()
            
            resultados["tablas"] = True
            print("✅ Acceso a tablas principales:")
            print(f"   - Clientes: {total_clientes:,}")
            print(f"   - Préstamos: {total_prestamos:,}")
            print(f"   - Pagos: {total_pagos:,}")
            print(f"   - Cuotas: {total_cuotas:,}")
        except Exception as e:
            resultados["tablas"] = False
            print(f"❌ Error accediendo a tablas: {e}")
        
    finally:
        db.close()
    
    return resultados

def main():
    """Función principal"""
    print("=" * 70)
    print("VERIFICACIÓN DE SINCRONIZACIÓN COMPLETA")
    print("Frontend ↔ Backend ↔ Base de Datos")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar cada componente
    resultados_frontend = verificar_frontend()
    resultados_backend = verificar_backend()
    resultados_bd = verificar_base_datos()
    
    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    
    # Frontend
    print("\n📱 FRONTEND:")
    frontend_ok = sum(1 for v in resultados_frontend.values() if v)
    frontend_total = len(resultados_frontend)
    for nombre, resultado in resultados_frontend.items():
        estado = "✅" if resultado else "❌"
        print(f"  {estado} {nombre}")
    print(f"  Total: {frontend_ok}/{frontend_total}")
    
    # Backend
    print("\n⚙️ BACKEND:")
    backend_ok = sum(1 for v in resultados_backend.values() if v)
    backend_total = len(resultados_backend)
    for nombre, resultado in resultados_backend.items():
        estado = "✅" if resultado else "❌"
        print(f"  {estado} {nombre}")
    print(f"  Total: {backend_ok}/{backend_total}")
    
    # Base de Datos
    print("\n🗄️ BASE DE DATOS:")
    bd_ok = sum(1 for v in resultados_bd.values() if v)
    bd_total = len(resultados_bd)
    for nombre, resultado in resultados_bd.items():
        estado = "✅" if resultado else "❌"
        print(f"  {estado} {nombre}")
    print(f"  Total: {bd_ok}/{bd_total}")
    
    # Estado general
    print("\n" + "-" * 70)
    total_ok = frontend_ok + backend_ok + bd_ok
    total_total = frontend_total + backend_total + bd_total
    print(f"ESTADO GENERAL: {total_ok}/{total_total} verificaciones exitosas")
    
    if total_ok == total_total:
        print("\n✅ TODO ESTÁ SINCRONIZADO Y ACTUALIZADO")
        print("Frontend, Backend y Base de Datos están correctamente configurados")
        return 0
    else:
        print("\n⚠️ ALGUNAS VERIFICACIONES FALLARON")
        print("Revisa los detalles arriba para identificar qué necesita actualizarse")
        return 1

if __name__ == "__main__":
    sys.exit(main())
