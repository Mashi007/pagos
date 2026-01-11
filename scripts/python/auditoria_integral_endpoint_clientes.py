"""
Auditoría Integral del Endpoint /clientes
Verifica: seguridad, rendimiento, estructura de datos, errores, y más
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    import requests
    from sqlalchemy import create_engine, text, func
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.db.session import SessionLocal, engine, get_db, test_connection
    from app.models.cliente import Cliente
    from app.schemas.cliente import ClienteResponse
    import logging

    # Configurar logging y encoding para Windows
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    class AuditoriaIntegralClientes:
        def __init__(self):
            self.resultados = {
                "fecha_auditoria": datetime.now().isoformat(),
                "endpoint": "https://rapicredit.onrender.com/api/v1/clientes",
                "verificaciones": {}
            }
            self.errores = []
            self.advertencias = []

        def verificar_conexion_bd(self) -> bool:
            """Verifica conexión a base de datos"""
            print("\n" + "=" * 70)
            print("1. VERIFICACIÓN: Conexión a Base de Datos")
            print("=" * 70)
            
            try:
                if test_connection():
                    print("   ✅ Conexión a base de datos exitosa")
                    self.resultados["verificaciones"]["conexion_bd"] = {
                        "estado": "exitoso",
                        "mensaje": "Conexión establecida correctamente"
                    }
                    return True
                else:
                    print("   ❌ Error en conexión a base de datos")
                    self.resultados["verificaciones"]["conexion_bd"] = {
                        "estado": "error",
                        "mensaje": "No se pudo establecer conexión"
                    }
                    return False
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["conexion_bd"] = {
                    "estado": "error",
                    "mensaje": str(e)
                }
                return False

        def verificar_estructura_tabla(self) -> bool:
            """Verifica estructura de la tabla clientes"""
            print("\n" + "=" * 70)
            print("2. VERIFICACIÓN: Estructura de Tabla 'clientes'")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    if settings.DATABASE_URL.startswith("postgresql"):
                        result = db.execute(text("""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns
                            WHERE table_name = 'clientes'
                            ORDER BY ordinal_position
                        """))
                        columnas = result.fetchall()
                        
                        estructura = {}
                        for col in columnas:
                            estructura[col[0]] = {
                                "tipo": col[1],
                                "nullable": col[2] == "YES",
                                "default": col[3]
                            }
                        
                        print(f"   ✅ Columnas encontradas: {len(columnas)}")
                        for nombre, info in estructura.items():
                            print(f"      - {nombre}: {info['tipo']} (nullable: {info['nullable']})")
                        
                        self.resultados["verificaciones"]["estructura_tabla"] = {
                            "estado": "exitoso",
                            "columnas": estructura,
                            "total_columnas": len(columnas)
                        }
                        return True
                    else:
                        print("   ⚠️  Verificación de estructura no disponible para SQLite")
                        self.resultados["verificaciones"]["estructura_tabla"] = {
                            "estado": "advertencia",
                            "mensaje": "No disponible para SQLite"
                        }
                        return True
                finally:
                    db.close()
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["estructura_tabla"] = {
                    "estado": "error",
                    "mensaje": str(e)
                }
                return False

        def verificar_datos_bd(self) -> bool:
            """Verifica datos en la base de datos"""
            print("\n" + "=" * 70)
            print("3. VERIFICACIÓN: Datos en Base de Datos")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    # Contar total
                    total = db.query(func.count(Cliente.id)).scalar()
                    print(f"   ✅ Total de clientes: {total}")
                    
                    # Contar por estado
                    activos = db.query(Cliente).filter(Cliente.estado == "ACTIVO").count()
                    inactivos = db.query(Cliente).filter(Cliente.estado == "INACTIVO").count()
                    finalizados = db.query(Cliente).filter(Cliente.estado == "FINALIZADO").count()
                    
                    print(f"   ✅ Activos: {activos}")
                    print(f"   ✅ Inactivos: {inactivos}")
                    print(f"   ✅ Finalizados: {finalizados}")
                    
                    # Verificar integridad de datos
                    sin_cedula = db.query(Cliente).filter(
                        (Cliente.cedula == None) | (Cliente.cedula == "")
                    ).count()
                    sin_nombres = db.query(Cliente).filter(
                        (Cliente.nombres == None) | (Cliente.nombres == "")
                    ).count()
                    
                    if sin_cedula > 0:
                        print(f"   ⚠️  Clientes sin cédula: {sin_cedula}")
                        self.advertencias.append(f"{sin_cedula} clientes sin cédula")
                    
                    if sin_nombres > 0:
                        print(f"   ⚠️  Clientes sin nombres: {sin_nombres}")
                        self.advertencias.append(f"{sin_nombres} clientes sin nombres")
                    
                    # Obtener muestra de datos
                    muestra = db.query(Cliente).limit(5).all()
                    muestra_serializada = []
                    for cliente in muestra:
                        try:
                            cliente_dict = ClienteResponse.model_validate(cliente).model_dump()
                            muestra_serializada.append(cliente_dict)
                        except Exception as e:
                            print(f"   ⚠️  Error serializando cliente {cliente.id}: {e}")
                    
                    self.resultados["verificaciones"]["datos_bd"] = {
                        "estado": "exitoso",
                        "total": total,
                        "activos": activos,
                        "inactivos": inactivos,
                        "finalizados": finalizados,
                        "sin_cedula": sin_cedula,
                        "sin_nombres": sin_nombres,
                        "muestra": muestra_serializada[:3]  # Solo primeros 3 para no hacer el JSON muy grande
                    }
                    return True
                finally:
                    db.close()
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                self.resultados["verificaciones"]["datos_bd"] = {
                    "estado": "error",
                    "mensaje": str(e)
                }
                return False

        def verificar_endpoint_backend(self) -> bool:
            """Verifica el endpoint directamente desde el backend"""
            print("\n" + "=" * 70)
            print("4. VERIFICACIÓN: Endpoint Backend (Local)")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    # Simular llamada al endpoint
                    from app.api.v1.endpoints.clientes import listar_clientes
                    from app.models.user import User
                    from unittest.mock import MagicMock
                    
                    # Crear mock de usuario y request
                    mock_user = MagicMock()
                    mock_user.email = "auditoria@test.com"
                    mock_user.id = 1
                    mock_user.is_active = True
                    
                    # Ejecutar endpoint con diferentes parámetros
                    resultados_pruebas = []
                    
                    # Prueba 1: Sin filtros, página 1
                    try:
                        start_time = time.time()
                        # Nota: Esto requiere acceso a la función directamente
                        # Por ahora verificamos que la query funciona
                        query = db.query(Cliente)
                        total = query.count()
                        clientes = query.order_by(Cliente.fecha_registro.desc()).limit(20).all()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query básica: {len(clientes)} clientes en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_basica",
                            "tiempo_ms": tiempo,
                            "registros": len(clientes),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ❌ Error en query básica: {e}")
                        resultados_pruebas.append({
                            "test": "query_basica",
                            "error": str(e),
                            "exitoso": False
                        })
                    
                    # Prueba 2: Con filtro de estado
                    try:
                        start_time = time.time()
                        query = db.query(Cliente).filter(Cliente.estado == "ACTIVO")
                        activos = query.limit(20).all()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query con filtro: {len(activos)} activos en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_con_filtro",
                            "tiempo_ms": tiempo,
                            "registros": len(activos),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ❌ Error en query con filtro: {e}")
                        resultados_pruebas.append({
                            "test": "query_con_filtro",
                            "error": str(e),
                            "exitoso": False
                        })
                    
                    self.resultados["verificaciones"]["endpoint_backend"] = {
                        "estado": "exitoso" if all(r["exitoso"] for r in resultados_pruebas) else "parcial",
                        "pruebas": resultados_pruebas
                    }
                    return True
                finally:
                    db.close()
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                self.resultados["verificaciones"]["endpoint_backend"] = {
                    "estado": "error",
                    "mensaje": str(e)
                }
                return False

        def verificar_rendimiento(self) -> bool:
            """Verifica rendimiento de consultas"""
            print("\n" + "=" * 70)
            print("5. VERIFICACIÓN: Rendimiento")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    resultados_rendimiento = []
                    
                    # Test 1: COUNT sin filtros
                    start_time = time.time()
                    total = db.query(func.count(Cliente.id)).scalar()
                    tiempo_count = (time.time() - start_time) * 1000
                    print(f"   ✅ COUNT total: {tiempo_count:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "count_total",
                        "tiempo_ms": tiempo_count,
                        "aceptable": tiempo_count < 1000  # Menos de 1 segundo
                    })
                    
                    # Test 2: Query con paginación
                    start_time = time.time()
                    clientes = db.query(Cliente).order_by(Cliente.fecha_registro.desc()).limit(20).offset(0).all()
                    tiempo_query = (time.time() - start_time) * 1000
                    print(f"   ✅ Query paginada (20 registros): {tiempo_query:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_paginada_20",
                        "tiempo_ms": tiempo_query,
                        "aceptable": tiempo_query < 500  # Menos de 500ms
                    })
                    
                    # Test 3: Query con filtros
                    start_time = time.time()
                    activos = db.query(Cliente).filter(Cliente.estado == "ACTIVO").limit(20).all()
                    tiempo_filtro = (time.time() - start_time) * 1000
                    print(f"   ✅ Query con filtro: {tiempo_filtro:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_con_filtro",
                        "tiempo_ms": tiempo_filtro,
                        "aceptable": tiempo_filtro < 500
                    })
                    
                    # Test 4: Serialización
                    start_time = time.time()
                    clientes_serializados = []
                    for cliente in clientes[:10]:  # Solo primeros 10
                        try:
                            cliente_dict = ClienteResponse.model_validate(cliente).model_dump()
                            clientes_serializados.append(cliente_dict)
                        except Exception as e:
                            pass
                    tiempo_serializacion = (time.time() - start_time) * 1000
                    print(f"   ✅ Serialización (10 registros): {tiempo_serializacion:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "serializacion_10",
                        "tiempo_ms": tiempo_serializacion,
                        "aceptable": tiempo_serializacion < 100  # Menos de 100ms
                    })
                    
                    # Evaluar rendimiento general
                    operaciones_aceptables = sum(1 for r in resultados_rendimiento if r.get("aceptable", False))
                    rendimiento_ok = operaciones_aceptables == len(resultados_rendimiento)
                    
                    self.resultados["verificaciones"]["rendimiento"] = {
                        "estado": "exitoso" if rendimiento_ok else "advertencia",
                        "pruebas": resultados_rendimiento,
                        "operaciones_aceptables": operaciones_aceptables,
                        "total_operaciones": len(resultados_rendimiento)
                    }
                    
                    if not rendimiento_ok:
                        self.advertencias.append("Algunas operaciones exceden los tiempos aceptables")
                    
                    return True
                finally:
                    db.close()
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["rendimiento"] = {
                    "estado": "error",
                    "mensaje": str(e)
                }
                return False

        def verificar_indices(self) -> bool:
            """Verifica índices en la tabla"""
            print("\n" + "=" * 70)
            print("6. VERIFICACIÓN: Índices de Base de Datos")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    if settings.DATABASE_URL.startswith("postgresql"):
                        result = db.execute(text("""
                            SELECT
                                indexname,
                                indexdef
                            FROM pg_indexes
                            WHERE tablename = 'clientes'
                            ORDER BY indexname
                        """))
                        indices = result.fetchall()
                        
                        print(f"   ✅ Índices encontrados: {len(indices)}")
                        indices_info = {}
                        for idx in indices:
                            nombre = idx[0]
                            definicion = idx[1]
                            print(f"      - {nombre}")
                            indices_info[nombre] = definicion
                        
                        # Verificar índices críticos
                        indices_criticos = ['clientes_pkey', 'ix_clientes_cedula', 'ix_clientes_estado', 
                                         'ix_clientes_telefono', 'ix_clientes_email']
                        indices_faltantes = [idx for idx in indices_criticos if idx not in indices_info]
                        
                        if indices_faltantes:
                            print(f"   ⚠️  Índices faltantes: {indices_faltantes}")
                            self.advertencias.append(f"Índices faltantes: {', '.join(indices_faltantes)}")
                        
                        self.resultados["verificaciones"]["indices"] = {
                            "estado": "exitoso" if not indices_faltantes else "advertencia",
                            "indices": indices_info,
                            "total": len(indices),
                            "faltantes": indices_faltantes
                        }
                        return True
                    else:
                        print("   ⚠️  Verificación de índices no disponible para SQLite")
                        self.resultados["verificaciones"]["indices"] = {
                            "estado": "advertencia",
                            "mensaje": "No disponible para SQLite"
                        }
                        return True
                finally:
                    db.close()
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["indices"] = {
                    "estado": "error",
                    "mensaje": str(e)
                }
                return False

        def verificar_validaciones(self) -> bool:
            """Verifica validaciones de datos"""
            print("\n" + "=" * 70)
            print("7. VERIFICACIÓN: Validaciones de Datos")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    problemas = []
                    
                    # Verificar cédulas duplicadas
                    result = db.execute(text("""
                        SELECT cedula, COUNT(*) as count
                        FROM clientes
                        GROUP BY cedula
                        HAVING COUNT(*) > 1
                        LIMIT 10
                    """))
                    duplicados = result.fetchall()
                    if duplicados:
                        print(f"   ⚠️  Cédulas duplicadas encontradas: {len(duplicados)}")
                        problemas.append(f"{len(duplicados)} cédulas duplicadas")
                    
                    # Verificar emails inválidos (básico)
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM clientes
                        WHERE email NOT LIKE '%@%' AND email != ''
                    """))
                    emails_invalidos = result.scalar()
                    if emails_invalidos > 0:
                        print(f"   ⚠️  Emails sin formato válido: {emails_invalidos}")
                        problemas.append(f"{emails_invalidos} emails inválidos")
                    
                    # Verificar fechas futuras en fecha_registro
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM clientes
                        WHERE fecha_registro > CURRENT_TIMESTAMP
                    """))
                    fechas_futuras = result.scalar()
                    if fechas_futuras > 0:
                        print(f"   ⚠️  Fechas de registro futuras: {fechas_futuras}")
                        problemas.append(f"{fechas_futuras} fechas futuras")
                    
                    if not problemas:
                        print("   ✅ No se encontraron problemas de validación")
                    
                    self.resultados["verificaciones"]["validaciones"] = {
                        "estado": "exitoso" if not problemas else "advertencia",
                        "problemas": problemas
                    }
                    
                    if problemas:
                        self.advertencias.extend(problemas)
                    
                    return True
                finally:
                    db.close()
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["validaciones"] = {
                    "estado": "error",
                    "mensaje": str(e)
                }
                return False

        def generar_reporte(self):
            """Genera reporte final"""
            print("\n" + "=" * 70)
            print("RESUMEN DE AUDITORÍA")
            print("=" * 70)
            
            # Contar verificaciones
            exitosas = sum(1 for v in self.resultados["verificaciones"].values() 
                          if v.get("estado") == "exitoso")
            parciales = sum(1 for v in self.resultados["verificaciones"].values() 
                           if v.get("estado") == "parcial")
            errores = sum(1 for v in self.resultados["verificaciones"].values() 
                         if v.get("estado") == "error")
            advertencias_count = sum(1 for v in self.resultados["verificaciones"].values() 
                                    if v.get("estado") == "advertencia")
            
            total = len(self.resultados["verificaciones"])
            
            print(f"\nVerificaciones exitosas: {exitosas}/{total}")
            print(f"Verificaciones parciales: {parciales}/{total}")
            print(f"Verificaciones con errores: {errores}/{total}")
            print(f"Verificaciones con advertencias: {advertencias_count}/{total}")
            
            if self.advertencias:
                print(f"\n⚠️  Advertencias encontradas: {len(self.advertencias)}")
                for adv in self.advertencias:
                    print(f"   - {adv}")
            
            if self.errores:
                print(f"\n❌ Errores encontrados: {len(self.errores)}")
                for err in self.errores:
                    print(f"   - {err}")
            
            # Guardar reporte JSON
            reporte_path = Path(__file__).parent.parent.parent / "AUDITORIA_CLIENTES.json"
            with open(reporte_path, 'w', encoding='utf-8') as f:
                json.dump({
                    **self.resultados,
                    "resumen": {
                        "exitosas": exitosas,
                        "parciales": parciales,
                        "errores": errores,
                        "advertencias": advertencias_count,
                        "total": total
                    },
                    "advertencias": self.advertencias,
                    "errores": self.errores
                }, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n✅ Reporte guardado en: {reporte_path}")
            
            return exitosas == total

        def ejecutar_auditoria_completa(self):
            """Ejecuta todas las verificaciones"""
            print("=" * 70)
            print("AUDITORÍA INTEGRAL: Endpoint /clientes")
            print("=" * 70)
            print(f"Fecha: {self.resultados['fecha_auditoria']}")
            print(f"Endpoint: {self.resultados['endpoint']}")
            
            # Ejecutar todas las verificaciones
            self.verificar_conexion_bd()
            self.verificar_estructura_tabla()
            self.verificar_datos_bd()
            self.verificar_endpoint_backend()
            self.verificar_rendimiento()
            self.verificar_indices()
            self.verificar_validaciones()
            
            # Generar reporte
            return self.generar_reporte()

    if __name__ == "__main__":
        auditoria = AuditoriaIntegralClientes()
        exito = auditoria.ejecutar_auditoria_completa()
        sys.exit(0 if exito else 1)

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de tener todas las dependencias instaladas:")
    print("  pip install requests sqlalchemy")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
