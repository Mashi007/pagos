#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar la conexión a BD del endpoint /chat-ai

Verifica:
1. Conexión básica a la base de datos
2. Acceso a todas las tablas principales
3. Consultas específicas usadas por el Chat AI
4. Configuración AI en BD
5. Índices creados para optimización
"""

import sys
import io
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

from sqlalchemy import text, func
from app.db.session import SessionLocal
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota
from app.models.configuracion_sistema import ConfiguracionSistema

def verificar_conexion_basica(db):
    """Verifica conexión básica a la BD"""
    print("\n" + "=" * 70)
    print("1. VERIFICACIÓN DE CONEXIÓN BÁSICA")
    print("=" * 70)
    
    try:
        resultado = db.execute(text("SELECT 1 as test"))
        row = resultado.fetchone()
        if row and row[0] == 1:
            print("✅ Conexión básica: OK")
            return True
        else:
            print("❌ Conexión básica: FALLO")
            return False
    except Exception as e:
        print(f"❌ Error en conexión básica: {e}")
        return False

def verificar_tablas_principales(db):
    """Verifica acceso a todas las tablas principales"""
    print("\n" + "=" * 70)
    print("2. VERIFICACIÓN DE TABLAS PRINCIPALES")
    print("=" * 70)
    
    tablas = {
        "clientes": Cliente,
        "prestamos": Prestamo,
        "pagos": Pago,
        "cuotas": Cuota,
        "configuracion_sistema": ConfiguracionSistema,
    }
    
    resultados = {}
    
    for nombre_tabla, modelo in tablas.items():
        try:
            count = db.query(modelo).count()
            resultados[nombre_tabla] = {"ok": True, "count": count}
            print(f"✅ Tabla '{nombre_tabla}': OK ({count:,} registros)")
        except Exception as e:
            resultados[nombre_tabla] = {"ok": False, "error": str(e)}
            print(f"❌ Tabla '{nombre_tabla}': ERROR - {e}")
    
    return all(r["ok"] for r in resultados.values())

def verificar_consultas_chat_ai(db):
    """Verifica consultas específicas usadas por el Chat AI"""
    print("\n" + "=" * 70)
    print("3. VERIFICACIÓN DE CONSULTAS DEL CHAT AI")
    print("=" * 70)
    
    consultas_ok = 0
    consultas_total = 0
    
    # Consulta 1: Resumen de clientes
    try:
        consultas_total += 1
        total_clientes = db.query(Cliente).count()
        clientes_activos = db.query(Cliente).filter(Cliente.estado == "ACTIVO").count()
        print(f"✅ Consulta clientes: OK (Total: {total_clientes}, Activos: {clientes_activos})")
        consultas_ok += 1
    except Exception as e:
        consultas_total += 1
        print(f"❌ Consulta clientes: ERROR - {e}")
    
    # Consulta 2: Resumen de préstamos
    try:
        consultas_total += 1
        total_prestamos = db.query(Prestamo).count()
        prestamos_aprobados = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()
        print(f"✅ Consulta préstamos: OK (Total: {total_prestamos}, Aprobados: {prestamos_aprobados})")
        consultas_ok += 1
    except Exception as e:
        consultas_total += 1
        print(f"❌ Consulta préstamos: ERROR - {e}")
    
    # Consulta 3: Resumen de pagos
    try:
        consultas_total += 1
        total_pagos = db.query(Pago).count()
        pagos_activos = db.query(Pago).filter(Pago.activo.is_(True)).count()
        print(f"✅ Consulta pagos: OK (Total: {total_pagos}, Activos: {pagos_activos})")
        consultas_ok += 1
    except Exception as e:
        consultas_total += 1
        print(f"❌ Consulta pagos: ERROR - {e}")
    
    # Consulta 4: Resumen de cuotas
    try:
        consultas_total += 1
        total_cuotas = db.query(Cuota).count()
        cuotas_pagadas = db.query(Cuota).filter(Cuota.estado == "PAGADA").count()
        print(f"✅ Consulta cuotas: OK (Total: {total_cuotas}, Pagadas: {cuotas_pagadas})")
        consultas_ok += 1
    except Exception as e:
        consultas_total += 1
        print(f"❌ Consulta cuotas: ERROR - {e}")
    
    # Consulta 5: GROUP BY con EXTRACT (usando índices funcionales)
    try:
        consultas_total += 1
        from sqlalchemy import extract
        from app.models.amortizacion import Cuota as CuotaModel
        query_cuotas_mes = db.query(
            extract("year", CuotaModel.fecha_vencimiento).label("año"),
            extract("month", CuotaModel.fecha_vencimiento).label("mes"),
            func.count(CuotaModel.id).label("total"),
        ).group_by(
            extract("year", CuotaModel.fecha_vencimiento),
            extract("month", CuotaModel.fecha_vencimiento)
        ).limit(5).all()
        
        print(f"✅ Consulta GROUP BY con EXTRACT: OK ({len(query_cuotas_mes)} meses encontrados)")
        consultas_ok += 1
    except Exception as e:
        consultas_total += 1
        print(f"❌ Consulta GROUP BY con EXTRACT: ERROR - {e}")
    
    # Consulta 6: JOIN entre cuotas y préstamos
    try:
        consultas_total += 1
        from app.models.amortizacion import Cuota as CuotaModel
        query_join = db.query(CuotaModel, Prestamo).join(
            Prestamo, CuotaModel.prestamo_id == Prestamo.id
        ).filter(Prestamo.estado == "APROBADO").limit(5).all()
        
        print(f"✅ Consulta JOIN cuotas-prestamos: OK ({len(query_join)} registros)")
        consultas_ok += 1
    except Exception as e:
        consultas_total += 1
        print(f"❌ Consulta JOIN cuotas-prestamos: ERROR - {e}")
    
    print(f"\n📊 Resumen: {consultas_ok}/{consultas_total} consultas exitosas")
    return consultas_ok == consultas_total

def verificar_configuracion_ai(db):
    """Verifica configuración AI en BD"""
    print("\n" + "=" * 70)
    print("4. VERIFICACIÓN DE CONFIGURACIÓN AI")
    print("=" * 70)
    
    try:
        configs = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.categoria == "AI"
        ).all()
        
        if not configs:
            print("⚠️ No hay configuración AI en BD")
            return False
        
        config_dict = {config.clave: config.valor for config in configs}
        
        # Verificar parámetros críticos
        parametros_criticos = {
            "activo": config_dict.get("activo", ""),
            "openai_api_key": "***" if config_dict.get("openai_api_key") else None,
            "modelo": config_dict.get("modelo", ""),
            "timeout_segundos": config_dict.get("timeout_segundos", ""),
            "cache_resumen_bd_ttl": config_dict.get("cache_resumen_bd_ttl", ""),
        }
        
        print(f"✅ Configuración AI encontrada: {len(configs)} parámetros")
        for clave, valor in parametros_criticos.items():
            if valor:
                print(f"   - {clave}: {'Configurado' if valor != '***' else 'Configurado (encriptado)'}")
            else:
                print(f"   ⚠️ {clave}: No configurado")
        
        # Verificar que AI está activo
        activo = config_dict.get("activo", "").lower() == "true"
        if activo:
            print("✅ AI está activo")
        else:
            print("⚠️ AI NO está activo")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando configuración AI: {e}")
        return False

def verificar_indices(db):
    """Verifica que los índices de optimización estén creados"""
    print("\n" + "=" * 70)
    print("5. VERIFICACIÓN DE ÍNDICES DE OPTIMIZACIÓN")
    print("=" * 70)
    
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
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname IN :indices
        """)
        
        # Convertir lista a tupla para SQL
        indices_tuple = tuple(indices_esperados)
        resultado = db.execute(query, {"indices": indices_tuple})
        indices_encontrados = {row[0]: row[1] for row in resultado.fetchall()}
        
        indices_faltantes = []
        for idx in indices_esperados:
            if idx in indices_encontrados:
                tabla = indices_encontrados[idx]
                print(f"✅ Índice '{idx}': OK (tabla: {tabla})")
            else:
                print(f"❌ Índice '{idx}': NO ENCONTRADO")
                indices_faltantes.append(idx)
        
        if indices_faltantes:
            print(f"\n⚠️ Índices faltantes: {len(indices_faltantes)}")
            return False
        else:
            print(f"\n✅ Todos los índices están creados ({len(indices_esperados)})")
            return True
            
    except Exception as e:
        print(f"❌ Error verificando índices: {e}")
        return False

def verificar_extension_pg_trgm(db):
    """Verifica que la extensión pg_trgm esté instalada"""
    print("\n" + "=" * 70)
    print("6. VERIFICACIÓN DE EXTENSIÓN pg_trgm")
    print("=" * 70)
    
    try:
        query = text("""
            SELECT extname, extversion, n.nspname
            FROM pg_extension e
            JOIN pg_namespace n ON e.extnamespace = n.oid
            WHERE extname = 'pg_trgm'
        """)
        resultado = db.execute(query)
        row = resultado.fetchone()
        
        if row:
            print(f"✅ Extensión pg_trgm: Instalada")
            print(f"   Versión: {row[1]}")
            print(f"   Schema: {row[2]}")
            return True
        else:
            print("❌ Extensión pg_trgm: NO instalada")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando extensión: {e}")
        return False

def main():
    """Función principal"""
    print("=" * 70)
    print("VERIFICACIÓN DE CONEXIÓN BD - ENDPOINT /chat-ai")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db = SessionLocal()
    resultados = {}
    
    try:
        # 1. Conexión básica
        resultados["conexion"] = verificar_conexion_basica(db)
        
        # 2. Tablas principales
        resultados["tablas"] = verificar_tablas_principales(db)
        
        # 3. Consultas del Chat AI
        resultados["consultas"] = verificar_consultas_chat_ai(db)
        
        # 4. Configuración AI
        resultados["config_ai"] = verificar_configuracion_ai(db)
        
        # 5. Índices
        resultados["indices"] = verificar_indices(db)
        
        # 6. Extensión pg_trgm
        resultados["extension"] = verificar_extension_pg_trgm(db)
        
        # Resumen final
        print("\n" + "=" * 70)
        print("RESUMEN FINAL")
        print("=" * 70)
        
        total_verificaciones = len(resultados)
        verificaciones_ok = sum(1 for v in resultados.values() if v)
        
        for nombre, resultado in resultados.items():
            estado = "✅ OK" if resultado else "❌ FALLO"
            print(f"{nombre.upper():20} {estado}")
        
        print("\n" + "-" * 70)
        print(f"Total: {verificaciones_ok}/{total_verificaciones} verificaciones exitosas")
        
        if verificaciones_ok == total_verificaciones:
            print("\n✅ TODAS LAS VERIFICACIONES EXITOSAS")
            print("El endpoint /chat-ai está correctamente conectado a la BD")
            return 0
        else:
            print("\n⚠️ ALGUNAS VERIFICACIONES FALLARON")
            print("Revisa los errores arriba para más detalles")
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
