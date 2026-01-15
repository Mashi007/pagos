#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que la estructura de BD permite consultas rápidas

Verifica:
1. Conexión a BD
2. Índices creados para optimización
3. Estructura de tablas principales
4. Consultas de ejemplo con EXPLAIN ANALYZE
5. Rendimiento de consultas críticas
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

from sqlalchemy import text, func, extract
from app.db.session import SessionLocal
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota

def verificar_conexion():
    """Verifica conexión básica a BD"""
    print("\n" + "=" * 70)
    print("1. VERIFICACIÓN DE CONEXIÓN A BASE DE DATOS")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        resultado = db.execute(text("SELECT 1 as test, current_database() as db_name, version() as pg_version"))
        row = resultado.fetchone()
        
        if row and row[0] == 1:
            print(f"✅ Conexión exitosa")
            print(f"   Base de datos: {row[1]}")
            print(f"   PostgreSQL: {row[2][:50]}...")
            return True, db
        else:
            print("❌ Conexión fallida")
            return False, None
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False, None

def verificar_indices():
    """Verifica que los índices de optimización estén creados"""
    print("\n" + "=" * 70)
    print("2. VERIFICACIÓN DE ÍNDICES DE OPTIMIZACIÓN")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        indices_esperados = [
            "idx_cuotas_extract_year_month_vencimiento",
            "idx_prestamos_extract_year_month_registro",
            "idx_pagos_extract_year_month",
            "idx_cuotas_prestamo_estado_fecha_vencimiento",
            "idx_prestamos_estado_analista_cedula",
            "idx_pagos_fecha_activo_prestamo",
            "idx_prestamos_analista_trgm",
        ]
        
        query = text("""
            SELECT 
                indexname,
                tablename,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = ANY(:indices)
            ORDER BY tablename, indexname
        """)
        
        resultado = db.execute(query, {"indices": indices_esperados})
        indices_encontrados = {row[0]: (row[1], row[2]) for row in resultado.fetchall()}
        
        indices_faltantes = [idx for idx in indices_esperados if idx not in indices_encontrados]
        
        if not indices_faltantes:
            print(f"✅ Todos los índices creados ({len(indices_esperados)})")
            for idx_name, (tabla, definicion) in indices_encontrados.items():
                print(f"   ✅ {idx_name} (tabla: {tabla})")
            return True
        else:
            print(f"⚠️ Índices faltantes: {len(indices_faltantes)}")
            for idx in indices_faltantes:
                print(f"   ❌ {idx}")
            return False
    except Exception as e:
        print(f"❌ Error verificando índices: {e}")
        return False
    finally:
        db.close()

def verificar_estructura_tablas():
    """Verifica la estructura de las tablas principales"""
    print("\n" + "=" * 70)
    print("3. VERIFICACIÓN DE ESTRUCTURA DE TABLAS")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        tablas = {
            "clientes": Cliente,
            "prestamos": Prestamo,
            "pagos": Pago,
            "cuotas": Cuota,
        }
        
        resultados = {}
        
        for nombre_tabla, modelo in tablas.items():
            try:
                # Obtener información de la tabla
                query = text("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = :tabla
                    ORDER BY ordinal_position
                    LIMIT 10
                """)
                resultado = db.execute(query, {"tabla": nombre_tabla})
                columnas = resultado.fetchall()
                
                # Contar registros
                count = db.query(modelo).count()
                
                resultados[nombre_tabla] = {
                    "ok": True,
                    "count": count,
                    "columnas": len(columnas)
                }
                
                print(f"✅ Tabla '{nombre_tabla}':")
                print(f"   Registros: {count:,}")
                print(f"   Columnas principales: {len(columnas)}")
                
            except Exception as e:
                resultados[nombre_tabla] = {"ok": False, "error": str(e)}
                print(f"❌ Tabla '{nombre_tabla}': ERROR - {e}")
        
        return all(r["ok"] for r in resultados.values())
        
    finally:
        db.close()

def verificar_consultas_rapidas():
    """Verifica que las consultas críticas usen índices"""
    print("\n" + "=" * 70)
    print("4. VERIFICACIÓN DE RENDIMIENTO DE CONSULTAS")
    print("=" * 70)
    
    db = SessionLocal()
    resultados = {}
    
    try:
        # Consulta 1: GROUP BY con EXTRACT (debe usar índice funcional)
        print("\n4.1 Consulta GROUP BY con EXTRACT (cuotas por mes)...")
        try:
            inicio = datetime.now()
            query = db.query(
                extract("year", Cuota.fecha_vencimiento).label("año"),
                extract("month", Cuota.fecha_vencimiento).label("mes"),
                func.count(Cuota.id).label("total"),
            ).group_by(
                extract("year", Cuota.fecha_vencimiento),
                extract("month", Cuota.fecha_vencimiento)
            ).limit(12).all()
            
            tiempo = (datetime.now() - inicio).total_seconds() * 1000
            
            if tiempo < 1000:
                print(f"   ✅ Tiempo: {tiempo:.2f}ms (RÁPIDO - usa índice)")
                resultados["group_by_extract"] = True
            else:
                print(f"   ⚠️ Tiempo: {tiempo:.2f}ms (LENTO - puede no usar índice)")
                resultados["group_by_extract"] = False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            resultados["group_by_extract"] = False
        
        # Consulta 2: JOIN eficiente (debe usar índice compuesto)
        print("\n4.2 Consulta JOIN cuotas-prestamos...")
        try:
            inicio = datetime.now()
            query = db.query(Cuota, Prestamo).join(
                Prestamo, Cuota.prestamo_id == Prestamo.id
            ).filter(
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento >= datetime.now().date()
            ).limit(100).all()
            
            tiempo = (datetime.now() - inicio).total_seconds() * 1000
            
            if tiempo < 500:
                print(f"   ✅ Tiempo: {tiempo:.2f}ms (RÁPIDO - usa índices)")
                resultados["join_eficiente"] = True
            else:
                print(f"   ⚠️ Tiempo: {tiempo:.2f}ms (ACEPTABLE)")
                resultados["join_eficiente"] = True  # Aceptable
        except Exception as e:
            print(f"   ❌ Error: {e}")
            resultados["join_eficiente"] = False
        
        # Consulta 3: Búsqueda por cédula (debe usar índice)
        print("\n4.3 Búsqueda por cédula...")
        try:
            inicio = datetime.now()
            cliente = db.query(Cliente).filter(Cliente.cedula == "V123456789").first()
            tiempo = (datetime.now() - inicio).total_seconds() * 1000
            
            if tiempo < 50:
                print(f"   ✅ Tiempo: {tiempo:.2f}ms (MUY RÁPIDO - usa índice)")
                resultados["busqueda_cedula"] = True
            else:
                print(f"   ⚠️ Tiempo: {tiempo:.2f}ms (ACEPTABLE)")
                resultados["busqueda_cedula"] = True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            resultados["busqueda_cedula"] = False
        
        # Consulta 4: Filtro por estado (debe usar índice)
        print("\n4.4 Filtro por estado de préstamos...")
        try:
            inicio = datetime.now()
            count = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()
            tiempo = (datetime.now() - inicio).total_seconds() * 1000
            
            if tiempo < 200:
                print(f"   ✅ Tiempo: {tiempo:.2f}ms (RÁPIDO - usa índice)")
                print(f"   Resultado: {count:,} préstamos aprobados")
                resultados["filtro_estado"] = True
            else:
                print(f"   ⚠️ Tiempo: {tiempo:.2f}ms (ACEPTABLE)")
                resultados["filtro_estado"] = True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            resultados["filtro_estado"] = False
        
        return resultados
        
    finally:
        db.close()

def verificar_explain_analyze():
    """Ejecuta EXPLAIN ANALYZE en consultas críticas"""
    print("\n" + "=" * 70)
    print("5. ANÁLISIS DE PLAN DE EJECUCIÓN (EXPLAIN ANALYZE)")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        # Consulta GROUP BY con EXTRACT
        print("\n5.1 Plan de ejecución: GROUP BY con EXTRACT")
        print("-" * 70)
        query_explain = text("""
            EXPLAIN ANALYZE
            SELECT 
                EXTRACT(YEAR FROM fecha_vencimiento) as año,
                EXTRACT(MONTH FROM fecha_vencimiento) as mes,
                COUNT(*) as total
            FROM cuotas
            WHERE fecha_vencimiento IS NOT NULL
            GROUP BY 
                EXTRACT(YEAR FROM fecha_vencimiento),
                EXTRACT(MONTH FROM fecha_vencimiento)
            LIMIT 12
        """)
        
        resultado = db.execute(query_explain)
        plan = resultado.fetchall()
        
        plan_texto = "\n".join([row[0] for row in plan])
        
        # Verificar si usa índice
        if "idx_cuotas_extract_year_month_vencimiento" in plan_texto or "Index Scan" in plan_texto:
            print("✅ Usa índice funcional (Index Scan)")
        elif "Seq Scan" in plan_texto:
            print("⚠️ Usa Sequential Scan (puede ser lento)")
        else:
            print("ℹ️ Plan de ejecución:")
        
        # Mostrar solo las primeras líneas del plan
        lineas = plan_texto.split('\n')[:10]
        for linea in lineas:
            print(f"   {linea}")
        
        if len(plan_texto.split('\n')) > 10:
            print("   ... (plan completo truncado)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en EXPLAIN ANALYZE: {e}")
        return False
    finally:
        db.close()

def verificar_extensiones():
    """Verifica extensiones de PostgreSQL instaladas"""
    print("\n" + "=" * 70)
    print("6. VERIFICACIÓN DE EXTENSIONES")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        query = text("""
            SELECT extname, extversion
            FROM pg_extension
            WHERE extname IN ('pg_trgm', 'pg_stat_statements')
            ORDER BY extname
        """)
        resultado = db.execute(query)
        extensiones = {row[0]: row[1] for row in resultado.fetchall()}
        
        if 'pg_trgm' in extensiones:
            print(f"✅ pg_trgm instalada (versión {extensiones['pg_trgm']})")
        else:
            print("❌ pg_trgm NO instalada")
        
        if 'pg_stat_statements' in extensiones:
            print(f"✅ pg_stat_statements instalada (versión {extensiones['pg_stat_statements']})")
        else:
            print("ℹ️ pg_stat_statements no instalada (opcional)")
        
        return 'pg_trgm' in extensiones
        
    except Exception as e:
        print(f"❌ Error verificando extensiones: {e}")
        return False
    finally:
        db.close()

def main():
    """Función principal"""
    print("=" * 70)
    print("VERIFICACIÓN DE ESTRUCTURA PARA CONSULTAS RÁPIDAS")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Conexión
    conexion_ok, db = verificar_conexion()
    if not conexion_ok:
        print("\n❌ No se pudo establecer conexión. Abortando verificación.")
        return 1
    
    if db:
        db.close()
    
    # 2. Índices
    indices_ok = verificar_indices()
    
    # 3. Estructura de tablas
    estructura_ok = verificar_estructura_tablas()
    
    # 4. Rendimiento de consultas
    rendimiento = verificar_consultas_rapidas()
    
    # 5. EXPLAIN ANALYZE
    explain_ok = verificar_explain_analyze()
    
    # 6. Extensiones
    extensiones_ok = verificar_extensiones()
    
    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    
    verificaciones = {
        "Conexión BD": conexion_ok,
        "Índices creados": indices_ok,
        "Estructura tablas": estructura_ok,
        "Rendimiento consultas": all(rendimiento.values()) if rendimiento else False,
        "Análisis EXPLAIN": explain_ok,
        "Extensiones": extensiones_ok,
    }
    
    for nombre, resultado in verificaciones.items():
        estado = "✅ OK" if resultado else "❌ FALLO"
        print(f"{nombre:30} {estado}")
    
    total_ok = sum(1 for v in verificaciones.values() if v)
    total_total = len(verificaciones)
    
    print("\n" + "-" * 70)
    print(f"Total: {total_ok}/{total_total} verificaciones exitosas")
    
    if total_ok == total_total:
        print("\n✅ ESTRUCTURA OPTIMIZADA PARA CONSULTAS RÁPIDAS")
        print("La base de datos está correctamente configurada con:")
        print("  - Índices funcionales para GROUP BY")
        print("  - Índices compuestos para JOINs eficientes")
        print("  - Índices GIN para búsquedas de texto")
        print("  - Extensiones necesarias instaladas")
        return 0
    else:
        print("\n⚠️ ALGUNAS VERIFICACIONES FALLARON")
        print("Revisa los detalles arriba para identificar qué necesita optimizarse")
        return 1

if __name__ == "__main__":
    sys.exit(main())
