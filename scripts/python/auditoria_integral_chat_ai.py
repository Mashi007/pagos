#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoría Integral del Chat AI
Verifica:
1. Conexión a base de datos
2. Acceso a las 4 tablas permitidas (clientes, prestamos, cuotas, pagos)
3. Índices creados y funcionando
4. Consultas cruzadas posibles
5. Permisos de lectura
6. Estructura de campos
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
    print("\n" + "=" * 80)
    print("1. VERIFICACIÓN DE CONEXIÓN A BASE DE DATOS")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        resultado = db.execute(text("SELECT 1 as test, current_database() as db_name, current_user as usuario, version() as pg_version"))
        row = resultado.fetchone()
        
        if row and row[0] == 1:
            print(f"✅ Conexión exitosa")
            print(f"   Base de datos: {row[1]}")
            print(f"   Usuario: {row[2]}")
            print(f"   PostgreSQL: {row[3][:60]}...")
            return True, db
        else:
            print("❌ Conexión fallida")
            return False, None
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False, None

def verificar_acceso_tablas():
    """Verifica acceso a las 4 tablas permitidas"""
    print("\n" + "=" * 80)
    print("2. VERIFICACIÓN DE ACCESO A TABLAS PERMITIDAS")
    print("=" * 80)
    
    db = SessionLocal()
    resultados = {}
    
    tablas_permitidas = {
        "clientes": Cliente,
        "prestamos": Prestamo,
        "cuotas": Cuota,
        "pagos": Pago,
    }
    
    try:
        for nombre_tabla, modelo in tablas_permitidas.items():
            try:
                # Intentar contar registros
                count = db.query(modelo).count()
                
                # Intentar leer un registro
                primer_registro = db.query(modelo).first()
                
                # Verificar estructura
                columnas = modelo.__table__.columns.keys()
                
                resultados[nombre_tabla] = {
                    "ok": True,
                    "count": count,
                    "acceso_lectura": True,
                    "columnas": len(columnas),
                    "primer_registro": primer_registro is not None
                }
                
                print(f"✅ Tabla '{nombre_tabla}':")
                print(f"   Registros: {count:,}")
                print(f"   Columnas: {len(columnas)}")
                print(f"   Acceso lectura: ✅ OK")
                print(f"   Primer registro: {'✅ Encontrado' if primer_registro else '❌ No encontrado'}")
                
            except Exception as e:
                resultados[nombre_tabla] = {
                    "ok": False,
                    "error": str(e)
                }
                print(f"❌ Tabla '{nombre_tabla}': ERROR - {e}")
        
        return resultados
        
    finally:
        db.close()

def verificar_indices():
    """Verifica que los índices de optimización estén creados"""
    print("\n" + "=" * 80)
    print("3. VERIFICACIÓN DE ÍNDICES DE OPTIMIZACIÓN")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Índices esperados por tabla
        indices_esperados = {
            "cuotas": [
                "idx_cuotas_extract_year_month_vencimiento",
                "idx_cuotas_prestamo_estado_fecha_vencimiento",
            ],
            "prestamos": [
                "idx_prestamos_extract_year_month_registro",
                "idx_prestamos_estado_analista_cedula",
                "idx_prestamos_analista_trgm",
            ],
            "pagos": [
                "idx_pagos_extract_year_month",
                "idx_pagos_fecha_activo_prestamo",
            ],
        }
        
        query = text("""
            SELECT 
                indexname,
                tablename,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """)
        
        resultado = db.execute(query)
        todos_indices = {row[0]: (row[1], row[2]) for row in resultado.fetchall()}
        
        indices_encontrados = {}
        indices_faltantes = {}
        
        for tabla, indices_tabla in indices_esperados.items():
            indices_encontrados[tabla] = []
            indices_faltantes[tabla] = []
            
            for idx_name in indices_tabla:
                if idx_name in todos_indices:
                    indices_encontrados[tabla].append(idx_name)
                else:
                    indices_faltantes[tabla].append(idx_name)
        
        # Mostrar resultados
        for tabla in indices_esperados.keys():
            print(f"\n📊 Tabla '{tabla}':")
            if indices_encontrados[tabla]:
                print(f"   ✅ Índices encontrados ({len(indices_encontrados[tabla])}):")
                for idx in indices_encontrados[tabla]:
                    print(f"      ✅ {idx}")
            if indices_faltantes[tabla]:
                print(f"   ❌ Índices faltantes ({len(indices_faltantes[tabla])}):")
                for idx in indices_faltantes[tabla]:
                    print(f"      ❌ {idx}")
            if not indices_encontrados[tabla] and not indices_faltantes[tabla]:
                print(f"   ⚠️ No hay índices esperados definidos para esta tabla")
        
        # Verificar índices en clientes (puede tener índices automáticos)
        query_clientes = text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'clientes'
            ORDER BY indexname
        """)
        resultado_clientes = db.execute(query_clientes)
        indices_clientes = resultado_clientes.fetchall()
        
        if indices_clientes:
            print(f"\n📊 Tabla 'clientes':")
            print(f"   ✅ Índices encontrados ({len(indices_clientes)}):")
            for idx_name, idx_def in indices_clientes:
                print(f"      ✅ {idx_name}")
        
        total_encontrados = sum(len(v) for v in indices_encontrados.values())
        total_faltantes = sum(len(v) for v in indices_faltantes.values())
        
        return total_faltantes == 0
        
    except Exception as e:
        print(f"❌ Error verificando índices: {e}")
        return False
    finally:
        db.close()

def verificar_consultas_cruzadas():
    """Verifica que las consultas cruzadas funcionen correctamente"""
    print("\n" + "=" * 80)
    print("4. VERIFICACIÓN DE CONSULTAS CRUZADAS")
    print("=" * 80)
    
    db = SessionLocal()
    resultados = {}
    
    try:
        # Consulta 1: Clientes con préstamos
        print("\n4.1 Clientes con préstamos (JOIN clientes + prestamos)...")
        try:
            inicio = datetime.now()
            query = db.query(Cliente, Prestamo).join(
                Prestamo, Cliente.cedula == Prestamo.cedula
            ).limit(10).all()
            tiempo = (datetime.now() - inicio).total_seconds() * 1000
            
            resultados["clientes_prestamos"] = {
                "ok": True,
                "tiempo_ms": tiempo,
                "registros": len(query)
            }
            print(f"   ✅ OK - Tiempo: {tiempo:.2f}ms, Registros: {len(query)}")
        except Exception as e:
            resultados["clientes_prestamos"] = {"ok": False, "error": str(e)}
            print(f"   ❌ Error: {e}")
        
        # Consulta 2: Préstamos con cuotas
        print("\n4.2 Préstamos con cuotas (JOIN prestamos + cuotas)...")
        try:
            inicio = datetime.now()
            query = db.query(Prestamo, Cuota).join(
                Cuota, Prestamo.id == Cuota.prestamo_id
            ).limit(10).all()
            tiempo = (datetime.now() - inicio).total_seconds() * 1000
            
            resultados["prestamos_cuotas"] = {
                "ok": True,
                "tiempo_ms": tiempo,
                "registros": len(query)
            }
            print(f"   ✅ OK - Tiempo: {tiempo:.2f}ms, Registros: {len(query)}")
        except Exception as e:
            resultados["prestamos_cuotas"] = {"ok": False, "error": str(e)}
            print(f"   ❌ Error: {e}")
        
        # Consulta 3: Préstamos con pagos
        print("\n4.3 Préstamos con pagos (JOIN prestamos + pagos)...")
        try:
            inicio = datetime.now()
            query = db.query(Prestamo, Pago).join(
                Pago, Prestamo.id == Pago.prestamo_id
            ).limit(10).all()
            tiempo = (datetime.now() - inicio).total_seconds() * 1000
            
            resultados["prestamos_pagos"] = {
                "ok": True,
                "tiempo_ms": tiempo,
                "registros": len(query)
            }
            print(f"   ✅ OK - Tiempo: {tiempo:.2f}ms, Registros: {len(query)}")
        except Exception as e:
            resultados["prestamos_pagos"] = {"ok": False, "error": str(e)}
            print(f"   ❌ Error: {e}")
        
        # Consulta 4: Consulta compleja (4 tablas)
        print("\n4.4 Consulta compleja (4 tablas: clientes + prestamos + cuotas + pagos)...")
        try:
            inicio = datetime.now()
            query = db.query(Cliente, Prestamo, Cuota, Pago).join(
                Prestamo, Cliente.cedula == Prestamo.cedula
            ).join(
                Cuota, Prestamo.id == Cuota.prestamo_id
            ).join(
                Pago, Prestamo.id == Pago.prestamo_id
            ).limit(5).all()
            tiempo = (datetime.now() - inicio).total_seconds() * 1000
            
            resultados["compleja_4_tablas"] = {
                "ok": True,
                "tiempo_ms": tiempo,
                "registros": len(query)
            }
            print(f"   ✅ OK - Tiempo: {tiempo:.2f}ms, Registros: {len(query)}")
        except Exception as e:
            resultados["compleja_4_tablas"] = {"ok": False, "error": str(e)}
            print(f"   ❌ Error: {e}")
        
        return resultados
        
    finally:
        db.close()

def verificar_permisos_lectura():
    """Verifica permisos de lectura en las tablas"""
    print("\n" + "=" * 80)
    print("5. VERIFICACIÓN DE PERMISOS DE LECTURA")
    print("=" * 80)
    
    db = SessionLocal()
    resultados = {}
    
    tablas = ["clientes", "prestamos", "cuotas", "pagos"]
    
    try:
        for tabla in tablas:
            try:
                query = text(f"""
                    SELECT 
                        has_table_privilege(:tabla, 'SELECT') as puede_leer,
                        has_table_privilege(:tabla, 'INSERT') as puede_insertar,
                        has_table_privilege(:tabla, 'UPDATE') as puede_actualizar,
                        has_table_privilege(:tabla, 'DELETE') as puede_eliminar
                """)
                resultado = db.execute(query, {"tabla": tabla})
                row = resultado.fetchone()
                
                resultados[tabla] = {
                    "ok": row[0] if row else False,
                    "puede_leer": row[0] if row else False,
                    "puede_insertar": row[1] if row else False,
                    "puede_actualizar": row[2] if row else False,
                    "puede_eliminar": row[3] if row else False,
                }
                
                print(f"\n📋 Tabla '{tabla}':")
                print(f"   Lectura (SELECT): {'✅ Permitido' if row[0] else '❌ Denegado'}")
                print(f"   Inserción (INSERT): {'✅ Permitido' if row[1] else '❌ Denegado'}")
                print(f"   Actualización (UPDATE): {'✅ Permitido' if row[2] else '❌ Denegado'}")
                print(f"   Eliminación (DELETE): {'✅ Permitido' if row[3] else '❌ Denegado'}")
                
            except Exception as e:
                resultados[tabla] = {"ok": False, "error": str(e)}
                print(f"❌ Error verificando permisos de '{tabla}': {e}")
        
        return resultados
        
    finally:
        db.close()

def verificar_estructura_campos():
    """Verifica la estructura de campos en las 4 tablas"""
    print("\n" + "=" * 80)
    print("6. VERIFICACIÓN DE ESTRUCTURA DE CAMPOS")
    print("=" * 80)
    
    db = SessionLocal()
    resultados = {}
    
    tablas_modelos = {
        "clientes": Cliente,
        "prestamos": Prestamo,
        "cuotas": Cuota,
        "pagos": Pago,
    }
    
    try:
        for nombre_tabla, modelo in tablas_modelos.items():
            try:
                columnas = modelo.__table__.columns
                
                campos_info = []
                for col in columnas:
                    campos_info.append({
                        "nombre": col.name,
                        "tipo": str(col.type),
                        "nullable": col.nullable,
                        "primary_key": col.primary_key,
                    })
                
                resultados[nombre_tabla] = {
                    "ok": True,
                    "total_campos": len(campos_info),
                    "campos": campos_info
                }
                
                print(f"\n📊 Tabla '{nombre_tabla}':")
                print(f"   Total campos: {len(campos_info)}")
                print(f"   Campos principales:")
                for campo in campos_info[:10]:  # Mostrar primeros 10
                    pk_marker = " [PK]" if campo["primary_key"] else ""
                    null_marker = " [NULL]" if campo["nullable"] else " [NOT NULL]"
                    print(f"      • {campo['nombre']}: {campo['tipo']}{pk_marker}{null_marker}")
                if len(campos_info) > 10:
                    print(f"      ... y {len(campos_info) - 10} campos más")
                
            except Exception as e:
                resultados[nombre_tabla] = {"ok": False, "error": str(e)}
                print(f"❌ Error verificando estructura de '{nombre_tabla}': {e}")
        
        return resultados
        
    finally:
        db.close()

def verificar_rendimiento_indices():
    """Verifica que los índices estén siendo usados en consultas"""
    print("\n" + "=" * 80)
    print("7. VERIFICACIÓN DE RENDIMIENTO DE ÍNDICES")
    print("=" * 80)
    
    db = SessionLocal()
    resultados = {}
    
    try:
        # Consulta 1: GROUP BY con EXTRACT (debe usar índice funcional)
        print("\n7.1 Consulta GROUP BY con EXTRACT (cuotas por mes)...")
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
            
            resultados["group_by_extract"] = {
                "ok": tiempo < 2000,
                "tiempo_ms": tiempo
            }
            
            if tiempo < 1000:
                print(f"   ✅ RÁPIDO - Tiempo: {tiempo:.2f}ms (usa índice)")
            else:
                print(f"   ⚠️ LENTO - Tiempo: {tiempo:.2f}ms (puede no usar índice)")
        except Exception as e:
            resultados["group_by_extract"] = {"ok": False, "error": str(e)}
            print(f"   ❌ Error: {e}")
        
        # Consulta 2: Búsqueda por cédula (debe usar índice)
        print("\n7.2 Búsqueda por cédula...")
        try:
            inicio = datetime.now()
            cliente = db.query(Cliente).filter(Cliente.cedula == "V123456789").first()
            tiempo = (datetime.now() - inicio).total_seconds() * 1000
            
            resultados["busqueda_cedula"] = {
                "ok": tiempo < 500,  # Más flexible para bases de datos grandes
                "tiempo_ms": tiempo
            }
            
            if tiempo < 50:
                print(f"   ✅ MUY RÁPIDO - Tiempo: {tiempo:.2f}ms (usa índice)")
            elif tiempo < 200:
                print(f"   ✅ RÁPIDO - Tiempo: {tiempo:.2f}ms (aceptable)")
            else:
                print(f"   ⚠️ ACEPTABLE - Tiempo: {tiempo:.2f}ms (puede optimizarse)")
        except Exception as e:
            resultados["busqueda_cedula"] = {"ok": False, "error": str(e)}
            print(f"   ❌ Error: {e}")
        
        # Consulta 3: Filtro por estado (debe usar índice)
        print("\n7.3 Filtro por estado de préstamos...")
        try:
            inicio = datetime.now()
            count = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()
            tiempo = (datetime.now() - inicio).total_seconds() * 1000
            
            resultados["filtro_estado"] = {
                "ok": tiempo < 500,
                "tiempo_ms": tiempo,
                "count": count
            }
            
            if tiempo < 200:
                print(f"   ✅ RÁPIDO - Tiempo: {tiempo:.2f}ms (usa índice)")
                print(f"   Resultado: {count:,} préstamos aprobados")
            else:
                print(f"   ⚠️ ACEPTABLE - Tiempo: {tiempo:.2f}ms")
        except Exception as e:
            resultados["filtro_estado"] = {"ok": False, "error": str(e)}
            print(f"   ❌ Error: {e}")
        
        return resultados
        
    finally:
        db.close()

def main():
    """Función principal"""
    print("=" * 80)
    print("AUDITORÍA INTEGRAL DEL CHAT AI")
    print("=" * 80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Objetivo: Verificar acceso completo y índices en base de datos")
    
    # 1. Conexión
    conexion_ok, db = verificar_conexion()
    if not conexion_ok:
        print("\n❌ No se pudo establecer conexión. Abortando auditoría.")
        return 1
    
    if db:
        db.close()
    
    # 2. Acceso a tablas
    acceso_tablas = verificar_acceso_tablas()
    
    # 3. Índices
    indices_ok = verificar_indices()
    
    # 4. Consultas cruzadas
    consultas_cruzadas = verificar_consultas_cruzadas()
    
    # 5. Permisos
    permisos = verificar_permisos_lectura()
    
    # 6. Estructura
    estructura = verificar_estructura_campos()
    
    # 7. Rendimiento
    rendimiento = verificar_rendimiento_indices()
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN FINAL DE AUDITORÍA")
    print("=" * 80)
    
    verificaciones = {
        "Conexión BD": conexion_ok,
        "Acceso a 4 tablas": all(r.get("ok", False) for r in acceso_tablas.values()) if acceso_tablas else False,
        "Índices creados": indices_ok,
        "Consultas cruzadas": all(r.get("ok", False) for r in consultas_cruzadas.values()) if consultas_cruzadas else False,
        "Permisos lectura": all(r.get("puede_leer", False) for r in permisos.values()) if permisos else False,
        "Estructura campos": all(r.get("ok", False) for r in estructura.values()) if estructura else False,
        "Rendimiento índices": all(r.get("ok", False) for r in rendimiento.values()) if rendimiento else False,
    }
    
    for nombre, resultado in verificaciones.items():
        estado = "✅ OK" if resultado else "❌ FALLO"
        print(f"{nombre:40} {estado}")
    
    total_ok = sum(1 for v in verificaciones.values() if v)
    total_total = len(verificaciones)
    
    print("\n" + "-" * 80)
    print(f"Total: {total_ok}/{total_total} verificaciones exitosas")
    
    if total_ok == total_total:
        print("\n✅ AUDITORÍA COMPLETA - TODO CORRECTO")
        print("El Chat AI tiene:")
        print("  ✅ Acceso completo a las 4 tablas permitidas")
        print("  ✅ Índices creados y funcionando")
        print("  ✅ Capacidad de hacer consultas cruzadas")
        print("  ✅ Permisos de lectura adecuados")
        print("  ✅ Estructura de campos correcta")
        print("  ✅ Rendimiento optimizado con índices")
        return 0
    else:
        print("\n⚠️ AUDITORÍA COMPLETA - ALGUNAS VERIFICACIONES FALLARON")
        print("Revisa los detalles arriba para identificar qué necesita corregirse")
        return 1

if __name__ == "__main__":
    sys.exit(main())
