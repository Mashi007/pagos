"""
Auditoría Integral del Endpoint /prestamos
Verifica: seguridad, rendimiento, estructura de datos, errores, y más
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from sqlalchemy import create_engine, text, func
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.db.session import SessionLocal, engine, get_db, test_connection
    from app.models.prestamo import Prestamo
    from app.models.cliente import Cliente
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

    BASE_URL = "https://rapicredit.onrender.com"
    REQUEST_TIMEOUT = 30

    class AuditoriaIntegralPrestamos:
        def __init__(self):
            self.resultados = {
                "fecha_auditoria": datetime.now().isoformat(),
                "url": "https://rapicredit.onrender.com/prestamos",
                "endpoint": "https://rapicredit.onrender.com/api/v1/prestamos",
                "verificaciones": {}
            }
            self.errores = []
            self.advertencias = []
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/json,application/xhtml+xml,*/*'
            })

        def verificar_conectividad(self):
            """Verifica conectividad a la URL"""
            print("\n" + "=" * 70)
            print("1. VERIFICACIÓN: Conectividad a URL")
            print("=" * 70)
            
            try:
                url = self.resultados["url"]
                start_time = time.time()
                response = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                tiempo_respuesta = (time.time() - start_time) * 1000
                
                resultado = {
                    "url": url,
                    "status_code": response.status_code,
                    "tiempo_respuesta_ms": round(tiempo_respuesta, 2),
                    "accesible": response.status_code == 200,
                    "url_final": response.url,
                    "redirecciones": len(response.history)
                }
                
                if response.status_code == 200:
                    print(f"   ✅ URL accesible - Status: {response.status_code}")
                    print(f"   ✅ Tiempo de respuesta: {tiempo_respuesta:.2f}ms")
                    print(f"   ✅ URL final: {response.url}")
                    
                    # Analizar HTML si es página web
                    try:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        titulo = soup.find('title')
                        if titulo:
                            resultado["titulo"] = titulo.get_text()
                            print(f"   ✅ Título: {resultado['titulo']}")
                    except Exception:
                        pass
                else:
                    print(f"   ⚠️  Status code: {response.status_code}")
                    self.advertencias.append(f"URL retornó status {response.status_code}")
                
                self.resultados["verificaciones"]["conectividad"] = resultado
                return resultado["accesible"]
                
            except requests.exceptions.Timeout:
                print("   ❌ Timeout al conectar")
                self.resultados["verificaciones"]["conectividad"] = {
                    "accesible": False,
                    "error": "Timeout"
                }
                self.errores.append("Timeout al conectar a la URL")
                return False
            except requests.exceptions.ConnectionError as e:
                print(f"   ❌ Error de conexión: {e}")
                self.resultados["verificaciones"]["conectividad"] = {
                    "accesible": False,
                    "error": str(e)
                }
                self.errores.append(f"Error de conexión: {e}")
                return False
            except Exception as e:
                print(f"   ❌ Error inesperado: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["conectividad"] = {
                    "accesible": False,
                    "error": str(e)
                }
                self.errores.append(f"Error inesperado: {e}")
                return False

        def verificar_conexion_bd(self) -> bool:
            """Verifica conexión a base de datos"""
            print("\n" + "=" * 70)
            print("2. VERIFICACIÓN: Conexión a Base de Datos")
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
                    self.errores.append("No se pudo establecer conexión a BD")
                    return False
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["conexion_bd"] = {
                    "estado": "error",
                    "mensaje": str(e)
                }
                self.errores.append(f"Error de conexión BD: {e}")
                return False

        def verificar_estructura_tabla(self) -> bool:
            """Verifica estructura de la tabla prestamos"""
            print("\n" + "=" * 70)
            print("3. VERIFICACIÓN: Estructura de Tabla 'prestamos'")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    if settings.DATABASE_URL.startswith("postgresql"):
                        result = db.execute(text("""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns
                            WHERE table_name = 'prestamos'
                            ORDER BY ordinal_position
                        """))
                        columnas = result.fetchall()
                        
                        estructura = {}
                        columnas_encontradas = []
                        for col in columnas:
                            estructura[col[0]] = {
                                "tipo": col[1],
                                "nullable": col[2] == "YES",
                                "default": str(col[3]) if col[3] else None
                            }
                            columnas_encontradas.append(col[0])
                        
                        print(f"   ✅ Columnas encontradas: {len(columnas)}")
                        for nombre, info in estructura.items():
                            nullable_str = "NULL" if info['nullable'] else "NOT NULL"
                            print(f"      - {nombre}: {info['tipo']} ({nullable_str})")
                        
                        # Verificar columnas críticas según el modelo
                        columnas_criticas = ['id', 'cliente_id', 'cedula', 'nombres', 'total_financiamiento', 
                                           'fecha_requerimiento', 'modalidad_pago', 'numero_cuotas', 
                                           'cuota_periodo', 'estado', 'fecha_registro']
                        columnas_opcionales = ['valor_activo', 'tasa_interes', 'fecha_base_calculo', 
                                              'producto', 'producto_financiero', 'concesionario', 'analista',
                                              'modelo_vehiculo', 'concesionario_id', 'analista_id', 
                                              'modelo_vehiculo_id', 'usuario_proponente', 'usuario_aprobador',
                                              'fecha_aprobacion', 'observaciones']
                        
                        columnas_faltantes_criticas = [c for c in columnas_criticas if c not in columnas_encontradas]
                        columnas_faltantes_opcionales = [c for c in columnas_opcionales if c not in columnas_encontradas]
                        
                        if columnas_faltantes_criticas:
                            print(f"   ❌ Columnas críticas faltantes: {columnas_faltantes_criticas}")
                            self.errores.append(f"Columnas críticas faltantes: {', '.join(columnas_faltantes_criticas)}")
                        
                        if columnas_faltantes_opcionales:
                            print(f"   ⚠️  Columnas opcionales faltantes: {columnas_faltantes_opcionales}")
                            self.advertencias.append(f"Columnas opcionales faltantes: {', '.join(columnas_faltantes_opcionales)}")
                        
                        self.resultados["verificaciones"]["estructura_tabla"] = {
                            "estado": "exitoso" if not columnas_faltantes_criticas else "error",
                            "columnas": estructura,
                            "total_columnas": len(columnas),
                            "columnas_criticas_faltantes": columnas_faltantes_criticas,
                            "columnas_opcionales_faltantes": columnas_faltantes_opcionales
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
                self.errores.append(f"Error verificando estructura: {e}")
                return False

        def verificar_datos_bd(self) -> bool:
            """Verifica datos en la base de datos"""
            print("\n" + "=" * 70)
            print("4. VERIFICACIÓN: Datos en Base de Datos")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    # Contar total
                    total = db.query(func.count(Prestamo.id)).scalar()
                    print(f"   ✅ Total de préstamos: {total}")
                    
                    if total == 0:
                        print("   ⚠️  No hay préstamos en la base de datos")
                        self.resultados["verificaciones"]["datos_bd"] = {
                            "estado": "advertencia",
                            "mensaje": "No hay datos",
                            "total": 0
                        }
                        self.advertencias.append("No hay préstamos en la base de datos")
                        return True
                    
                    # Contar por estado
                    estados = db.query(Prestamo.estado, func.count(Prestamo.id)).group_by(Prestamo.estado).all()
                    estados_dict = {estado: count for estado, count in estados}
                    
                    print("   ✅ Distribución por estado:")
                    for estado, count in estados_dict.items():
                        print(f"      - {estado}: {count}")
                    
                    # Contar por modalidad de pago
                    modalidades = db.query(Prestamo.modalidad_pago, func.count(Prestamo.id)).group_by(Prestamo.modalidad_pago).all()
                    modalidades_dict = {modalidad: count for modalidad, count in modalidades}
                    
                    print("   ✅ Distribución por modalidad de pago:")
                    for modalidad, count in modalidades_dict.items():
                        print(f"      - {modalidad}: {count}")
                    
                    # Estadísticas financieras
                    total_financiamiento = db.query(func.sum(Prestamo.total_financiamiento)).scalar()
                    promedio_financiamiento = db.query(func.avg(Prestamo.total_financiamiento)).scalar()
                    
                    print(f"   ✅ Total financiamiento: ${total_financiamiento:,.2f}" if total_financiamiento else "   ⚠️  Total financiamiento: $0.00")
                    print(f"   ✅ Promedio financiamiento: ${promedio_financiamiento:,.2f}" if promedio_financiamiento else "   ⚠️  Promedio financiamiento: $0.00")
                    
                    # Verificar integridad de datos usando queries raw para evitar problemas con columnas faltantes
                    sin_cliente_id = db.execute(text("""
                        SELECT COUNT(*) FROM prestamos WHERE cliente_id IS NULL
                    """)).scalar()
                    sin_cedula = db.execute(text("""
                        SELECT COUNT(*) FROM prestamos WHERE cedula IS NULL OR cedula = ''
                    """)).scalar()
                    sin_total_financiamiento = db.execute(text("""
                        SELECT COUNT(*) FROM prestamos WHERE total_financiamiento IS NULL OR total_financiamiento = 0
                    """)).scalar()
                    
                    if sin_cliente_id > 0:
                        print(f"   ⚠️  Préstamos sin cliente_id: {sin_cliente_id}")
                        self.advertencias.append(f"{sin_cliente_id} préstamos sin cliente_id")
                    
                    if sin_cedula > 0:
                        print(f"   ⚠️  Préstamos sin cédula: {sin_cedula}")
                        self.advertencias.append(f"{sin_cedula} préstamos sin cédula")
                    
                    if sin_total_financiamiento > 0:
                        print(f"   ⚠️  Préstamos sin total_financiamiento: {sin_total_financiamiento}")
                        self.advertencias.append(f"{sin_total_financiamiento} préstamos sin total_financiamiento")
                    
                    # Verificar relaciones usando queries raw
                    con_cliente = db.execute(text("""
                        SELECT COUNT(*) FROM prestamos WHERE cliente_id IS NOT NULL
                    """)).scalar()
                    sin_cliente = total - con_cliente
                    
                    print(f"   ✅ Préstamos con cliente_id: {con_cliente}")
                    print(f"   ✅ Préstamos sin cliente_id: {sin_cliente}")
                    
                    # Obtener muestra de datos usando query raw
                    muestra_result = db.execute(text("""
                        SELECT id, cedula, nombres, estado, total_financiamiento, modalidad_pago, numero_cuotas
                        FROM prestamos
                        ORDER BY id DESC
                        LIMIT 5
                    """)).fetchall()
                    muestra_serializada = []
                    for row in muestra_result:
                        try:
                            prestamo_dict = {
                                "id": row[0],
                                "cedula": row[1],
                                "nombres": row[2],
                                "estado": row[3],
                                "total_financiamiento": float(row[4]) if row[4] else None,
                                "modalidad_pago": row[5],
                                "numero_cuotas": row[6]
                            }
                            muestra_serializada.append(prestamo_dict)
                        except Exception as e:
                            print(f"   ⚠️  Error serializando préstamo {row[0]}: {e}")
                    
                    self.resultados["verificaciones"]["datos_bd"] = {
                        "estado": "exitoso",
                        "total": total,
                        "por_estado": estados_dict,
                        "por_modalidad": modalidades_dict,
                        "total_financiamiento": float(total_financiamiento) if total_financiamiento else 0,
                        "promedio_financiamiento": float(promedio_financiamiento) if promedio_financiamiento else 0,
                        "sin_cliente_id": sin_cliente_id,
                        "sin_cedula": sin_cedula,
                        "sin_total_financiamiento": sin_total_financiamiento,
                        "con_cliente": con_cliente,
                        "sin_cliente": sin_cliente,
                        "muestra": muestra_serializada[:3]
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
                self.errores.append(f"Error verificando datos: {e}")
                return False

        def verificar_endpoint_backend(self) -> bool:
            """Verifica el endpoint directamente desde el backend"""
            print("\n" + "=" * 70)
            print("5. VERIFICACIÓN: Endpoint Backend (Local)")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    resultados_pruebas = []
                    
                    # Prueba 1: Query básica usando raw SQL para evitar problemas con columnas faltantes
                    try:
                        start_time = time.time()
                        total = db.execute(text("SELECT COUNT(*) FROM prestamos")).scalar()
                        prestamos = db.execute(text("""
                            SELECT id, cedula, nombres, estado, total_financiamiento, modalidad_pago
                            FROM prestamos
                            ORDER BY id DESC
                            LIMIT 20
                        """)).fetchall()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query básica: {len(prestamos)} préstamos en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_basica",
                            "tiempo_ms": tiempo,
                            "registros": len(prestamos),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ❌ Error en query básica: {e}")
                        resultados_pruebas.append({
                            "test": "query_basica",
                            "error": str(e),
                            "exitoso": False
                        })
                    
                    # Prueba 2: Con filtro de estado usando raw SQL
                    try:
                        start_time = time.time()
                        aprobados = db.execute(text("""
                            SELECT id, cedula, nombres, estado, total_financiamiento
                            FROM prestamos
                            WHERE estado = 'APROBADO'
                            LIMIT 20
                        """)).fetchall()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query con filtro de estado: {len(aprobados)} aprobados en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_con_filtro_estado",
                            "tiempo_ms": tiempo,
                            "registros": len(aprobados),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ❌ Error en query con filtro: {e}")
                        resultados_pruebas.append({
                            "test": "query_con_filtro_estado",
                            "error": str(e),
                            "exitoso": False
                        })
                    
                    # Prueba 3: Con join a cliente usando raw SQL
                    try:
                        start_time = time.time()
                        prestamos_con_cliente = db.execute(text("""
                            SELECT p.id, p.cedula, p.nombres, p.estado, c.nombres as cliente_nombre
                            FROM prestamos p
                            LEFT JOIN clientes c ON p.cliente_id = c.id
                            LIMIT 20
                        """)).fetchall()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query con join cliente: {len(prestamos_con_cliente)} préstamos en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_con_join_cliente",
                            "tiempo_ms": tiempo,
                            "registros": len(prestamos_con_cliente),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ❌ Error en query con join: {e}")
                        resultados_pruebas.append({
                            "test": "query_con_join_cliente",
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
                self.errores.append(f"Error verificando endpoint backend: {e}")
                return False

        def verificar_rendimiento(self) -> bool:
            """Verifica rendimiento de consultas"""
            print("\n" + "=" * 70)
            print("6. VERIFICACIÓN: Rendimiento")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    resultados_rendimiento = []
                    
                    # Test 1: COUNT sin filtros
                    start_time = time.time()
                    total = db.query(func.count(Prestamo.id)).scalar()
                    tiempo_count = (time.time() - start_time) * 1000
                    print(f"   ✅ COUNT total: {tiempo_count:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "count_total",
                        "tiempo_ms": tiempo_count,
                        "aceptable": tiempo_count < 1000
                    })
                    
                    # Test 2: Query con paginación usando raw SQL
                    start_time = time.time()
                    prestamos = db.execute(text("""
                        SELECT id, cedula, nombres, estado, total_financiamiento
                        FROM prestamos
                        ORDER BY id DESC
                        LIMIT 20 OFFSET 0
                    """)).fetchall()
                    tiempo_query = (time.time() - start_time) * 1000
                    print(f"   ✅ Query paginada (20 registros): {tiempo_query:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_paginada_20",
                        "tiempo_ms": tiempo_query,
                        "aceptable": tiempo_query < 500
                    })
                    
                    # Test 3: Query con filtros usando raw SQL
                    start_time = time.time()
                    aprobados = db.execute(text("""
                        SELECT id, cedula, nombres, estado
                        FROM prestamos
                        WHERE estado = 'APROBADO'
                        LIMIT 20
                    """)).fetchall()
                    tiempo_filtro = (time.time() - start_time) * 1000
                    print(f"   ✅ Query con filtro: {tiempo_filtro:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_con_filtro",
                        "tiempo_ms": tiempo_filtro,
                        "aceptable": tiempo_filtro < 500
                    })
                    
                    # Test 4: Query con agregación
                    start_time = time.time()
                    suma = db.query(func.sum(Prestamo.total_financiamiento)).scalar()
                    tiempo_agregacion = (time.time() - start_time) * 1000
                    print(f"   ✅ Query con agregación (SUM): {tiempo_agregacion:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_con_agregacion",
                        "tiempo_ms": tiempo_agregacion,
                        "aceptable": tiempo_agregacion < 1000
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
                self.errores.append(f"Error verificando rendimiento: {e}")
                return False

        def verificar_indices(self) -> bool:
            """Verifica índices en la tabla"""
            print("\n" + "=" * 70)
            print("7. VERIFICACIÓN: Índices de Base de Datos")
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
                            WHERE tablename = 'prestamos'
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
                        
                        # Verificar índices críticos según el modelo
                        indices_criticos = ['prestamos_pkey', 'ix_prestamos_id', 'ix_prestamos_cliente_id', 
                                         'ix_prestamos_cedula', 'ix_prestamos_estado', 'ix_prestamos_fecha_registro',
                                         'ix_prestamos_concesionario_id', 'ix_prestamos_analista_id', 
                                         'ix_prestamos_modelo_vehiculo_id']
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
                self.errores.append(f"Error verificando índices: {e}")
                return False

        def verificar_validaciones(self) -> bool:
            """Verifica validaciones de datos"""
            print("\n" + "=" * 70)
            print("8. VERIFICACIÓN: Validaciones de Datos")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    problemas = []
                    
                    # Verificar estados válidos
                    estados_validos = ['DRAFT', 'EN_REVISION', 'APROBADO', 'RECHAZADO']
                    result = db.execute(text("""
                        SELECT estado, COUNT(*) as count
                        FROM prestamos
                        GROUP BY estado
                    """))
                    estados_encontrados = {row[0]: row[1] for row in result.fetchall()}
                    estados_invalidos = [e for e in estados_encontrados.keys() if e not in estados_validos]
                    if estados_invalidos:
                        print(f"   ⚠️  Estados inválidos encontrados: {estados_invalidos}")
                        problemas.append(f"Estados inválidos: {', '.join(estados_invalidos)}")
                    
                    # Verificar modalidades válidas
                    modalidades_validas = ['MENSUAL', 'QUINCENAL', 'SEMANAL']
                    result = db.execute(text("""
                        SELECT modalidad_pago, COUNT(*) as count
                        FROM prestamos
                        GROUP BY modalidad_pago
                    """))
                    modalidades_encontradas = {row[0]: row[1] for row in result.fetchall()}
                    modalidades_invalidas = [m for m in modalidades_encontradas.keys() if m not in modalidades_validas]
                    if modalidades_invalidas:
                        print(f"   ⚠️  Modalidades inválidas encontradas: {modalidades_invalidas}")
                        problemas.append(f"Modalidades inválidas: {', '.join(modalidades_invalidas)}")
                    
                    # Verificar fechas futuras en fecha_registro
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM prestamos
                        WHERE fecha_registro > CURRENT_TIMESTAMP
                    """))
                    fechas_futuras = result.scalar()
                    if fechas_futuras > 0:
                        print(f"   ⚠️  Fechas de registro futuras: {fechas_futuras}")
                        problemas.append(f"{fechas_futuras} fechas futuras")
                    
                    # Verificar clientes huérfanos
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM prestamos p
                        LEFT JOIN clientes c ON p.cliente_id = c.id
                        WHERE p.cliente_id IS NOT NULL AND c.id IS NULL
                    """))
                    clientes_huerfanos = result.scalar()
                    if clientes_huerfanos > 0:
                        print(f"   ⚠️  Préstamos con cliente_id inexistente: {clientes_huerfanos}")
                        problemas.append(f"{clientes_huerfanos} préstamos con cliente_id inexistente")
                    
                    # Verificar montos negativos o cero
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM prestamos
                        WHERE total_financiamiento <= 0
                    """))
                    montos_invalidos = result.scalar()
                    if montos_invalidos > 0:
                        print(f"   ⚠️  Préstamos con monto inválido (<=0): {montos_invalidos}")
                        problemas.append(f"{montos_invalidos} préstamos con monto inválido")
                    
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
                self.errores.append(f"Error verificando validaciones: {e}")
                return False

        def verificar_endpoint_api(self) -> bool:
            """Verifica el endpoint de la API (sin autenticación)"""
            print("\n" + "=" * 70)
            print("9. VERIFICACIÓN: Endpoint API (Producción)")
            print("=" * 70)
            
            try:
                endpoint_url = self.resultados["endpoint"]
                
                # Intentar acceder al endpoint (probablemente requerirá autenticación)
                start_time = time.time()
                response = self.session.get(endpoint_url, timeout=REQUEST_TIMEOUT)
                tiempo_respuesta = (time.time() - start_time) * 1000
                
                resultado = {
                    "url": endpoint_url,
                    "status_code": response.status_code,
                    "tiempo_respuesta_ms": round(tiempo_respuesta, 2),
                    "requiere_auth": response.status_code in [401, 403],
                    "existe": response.status_code != 404
                }
                
                if response.status_code == 200:
                    print(f"   ✅ Endpoint accesible - Status: {response.status_code}")
                    print(f"   ✅ Tiempo de respuesta: {tiempo_respuesta:.2f}ms")
                    try:
                        data = response.json()
                        resultado["tiene_datos"] = "data" in data or "items" in data
                    except:
                        pass
                elif response.status_code in [401, 403]:
                    print(f"   ✅ Endpoint existe pero requiere autenticación (Status {response.status_code})")
                elif response.status_code == 404:
                    print(f"   ❌ Endpoint no encontrado")
                    self.errores.append("Endpoint no encontrado")
                else:
                    print(f"   ⚠️  Status code: {response.status_code}")
                    self.advertencias.append(f"Endpoint retornó status {response.status_code}")
                
                self.resultados["verificaciones"]["endpoint_api"] = resultado
                return resultado["existe"]
                
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["endpoint_api"] = {
                    "existe": False,
                    "error": str(e)
                }
                self.errores.append(f"Error verificando endpoint API: {e}")
                return False

        def generar_reporte(self):
            """Genera reporte final"""
            print("\n" + "=" * 70)
            print("RESUMEN DE AUDITORÍA")
            print("=" * 70)
            
            # Contar verificaciones
            exitosas = sum(1 for v in self.resultados["verificaciones"].values() 
                          if isinstance(v, dict) and v.get("estado") == "exitoso")
            parciales = sum(1 for v in self.resultados["verificaciones"].values() 
                           if isinstance(v, dict) and v.get("estado") == "parcial")
            errores = sum(1 for v in self.resultados["verificaciones"].values() 
                         if isinstance(v, dict) and v.get("estado") == "error")
            advertencias_count = sum(1 for v in self.resultados["verificaciones"].values() 
                                    if isinstance(v, dict) and v.get("estado") == "advertencia")
            
            # También contar por accesible
            accesibles = sum(1 for v in self.resultados["verificaciones"].values() 
                           if isinstance(v, dict) and v.get("accesible") == True)
            
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
            reporte_path = Path(__file__).parent.parent.parent / "Documentos" / "Auditorias" / "AUDITORIA_PRESTAMOS.json"
            reporte_path.parent.mkdir(parents=True, exist_ok=True)
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
            
            # Generar reporte Markdown
            self.generar_reporte_markdown()
            
            return exitosas == total

        def generar_reporte_markdown(self):
            """Genera un reporte en formato Markdown"""
            ruta_md = Path(__file__).parent.parent.parent / "AUDITORIA_INTEGRAL_PRESTAMOS.md"
            
            with open(ruta_md, 'w', encoding='utf-8') as f:
                f.write("# 🔍 AUDITORÍA INTEGRAL: Endpoint /prestamos\n\n")
                f.write(f"**Fecha de auditoría:** {datetime.now().strftime('%Y-%m-%d')}  \n")
                f.write(f"**URL verificada:** `{self.resultados['url']}`  \n")
                f.write(f"**Endpoint API:** `{self.resultados['endpoint']}`  \n")
                f.write(f"**Script ejecutado:** `scripts/python/auditoria_integral_endpoint_prestamos.py`  \n")
                
                # Determinar estado general
                exitosas = sum(1 for v in self.resultados["verificaciones"].values() 
                              if isinstance(v, dict) and v.get("estado") == "exitoso")
                errores = sum(1 for v in self.resultados["verificaciones"].values() 
                             if isinstance(v, dict) and v.get("estado") == "error")
                total = len(self.resultados["verificaciones"])
                
                if errores == 0:
                    estado = "✅ **AUDITORÍA COMPLETA**"
                elif exitosas >= total * 0.7:
                    estado = "⚠️ **AUDITORÍA COMPLETA CON ADVERTENCIAS**"
                else:
                    estado = "❌ **AUDITORÍA CON ERRORES**"
                
                f.write(f"**Estado:** {estado}\n\n")
                f.write("---\n\n")
                
                f.write("## 📊 RESUMEN EJECUTIVO\n\n")
                f.write("### Resultados de la Auditoría\n\n")
                f.write("| Verificación | Estado | Detalles |\n")
                f.write("|-------------|--------|----------|\n")
                
                # Mapear verificaciones
                verificaciones_nombres = {
                    "conectividad": "Conectividad a URL",
                    "conexion_bd": "Conexión a Base de Datos",
                    "estructura_tabla": "Estructura de Tabla",
                    "datos_bd": "Datos en BD",
                    "endpoint_backend": "Endpoint Backend",
                    "rendimiento": "Rendimiento",
                    "indices": "Índices",
                    "validaciones": "Validaciones",
                    "endpoint_api": "Endpoint API"
                }
                
                for key, nombre in verificaciones_nombres.items():
                    if key in self.resultados["verificaciones"]:
                        v = self.resultados["verificaciones"][key]
                        if isinstance(v, dict):
                            estado_emoji = "✅" if v.get("estado") == "exitoso" or v.get("accesible") else "❌" if v.get("estado") == "error" else "⚠️"
                            estado_texto = v.get("estado", "N/A")
                            detalles = ""
                            if key == "conectividad":
                                detalles = f"Status {v.get('status_code')}, {v.get('tiempo_respuesta_ms', 0)}ms"
                            elif key == "datos_bd":
                                detalles = f"{v.get('total', 0)} préstamos"
                            elif key == "estructura_tabla":
                                detalles = f"{v.get('total_columnas', 0)} columnas"
                            elif key == "indices":
                                detalles = f"{v.get('total', 0)} índices"
                            f.write(f"| {nombre} | {estado_emoji} {estado_texto.upper()} | {detalles} |\n")
                
                f.write("\n")
                f.write(f"**Total:** {exitosas}/{total} verificaciones exitosas")
                if errores > 0:
                    f.write(f", {errores} con errores")
                if len(self.advertencias) > 0:
                    f.write(f", {len(self.advertencias)} advertencias")
                f.write(" ⚠️\n\n")
                f.write("---\n\n")
                
                # Detalles de cada verificación
                f.write("## 🔍 DETALLES DE VERIFICACIÓN\n\n")
                for key, nombre in verificaciones_nombres.items():
                    if key in self.resultados["verificaciones"]:
                        v = self.resultados["verificaciones"][key]
                        estado_emoji = "✅" if v.get("estado") == "exitoso" or v.get("accesible") else "❌" if v.get("estado") == "error" else "⚠️"
                        f.write(f"### {nombre} {estado_emoji}\n\n")
                        
                        if key == "conectividad":
                            f.write(f"- **URL:** {v.get('url')}\n")
                            f.write(f"- **Status Code:** {v.get('status_code')}\n")
                            f.write(f"- **Tiempo de respuesta:** {v.get('tiempo_respuesta_ms')}ms\n")
                            f.write(f"- **Accesible:** {'Sí' if v.get('accesible') else 'No'}\n")
                        elif key == "datos_bd":
                            f.write(f"- **Total de préstamos:** {v.get('total', 0)}\n")
                            if v.get('por_estado'):
                                f.write("- **Distribución por estado:**\n")
                                for estado, count in v.get('por_estado', {}).items():
                                    f.write(f"  - {estado}: {count}\n")
                            if v.get('total_financiamiento'):
                                f.write(f"- **Total financiamiento:** ${v.get('total_financiamiento', 0):,.2f}\n")
                        elif key == "estructura_tabla":
                            f.write(f"- **Total de columnas:** {v.get('total_columnas', 0)}\n")
                            if v.get('columnas_criticas_faltantes'):
                                f.write(f"- **⚠️ Columnas críticas faltantes:** {', '.join(v.get('columnas_criticas_faltantes', []))}\n")
                        elif key == "indices":
                            f.write(f"- **Total de índices:** {v.get('total', 0)}\n")
                            if v.get('faltantes'):
                                f.write(f"- **⚠️ Índices faltantes:** {', '.join(v.get('faltantes', []))}\n")
                        elif key == "validaciones":
                            if v.get('problemas'):
                                f.write("- **⚠️ Problemas encontrados:**\n")
                                for problema in v.get('problemas', []):
                                    f.write(f"  - {problema}\n")
                            else:
                                f.write("- **✅ No se encontraron problemas**\n")
                        
                        f.write("\n")
                
                # Recomendaciones
                if self.advertencias or self.errores:
                    f.write("## ⚠️ RECOMENDACIONES\n\n")
                    if self.errores:
                        f.write("### Prioridad Alta 🔴\n\n")
                        for err in self.errores:
                            f.write(f"- {err}\n")
                        f.write("\n")
                    if self.advertencias:
                        f.write("### Prioridad Media 🟡\n\n")
                        for adv in self.advertencias[:10]:  # Limitar a 10
                            f.write(f"- {adv}\n")
                        f.write("\n")
            
            print(f"[INFO] Reporte Markdown guardado en: {ruta_md}")

        def ejecutar_auditoria_completa(self):
            """Ejecuta todas las verificaciones"""
            print("=" * 70)
            print("AUDITORÍA INTEGRAL: Endpoint /prestamos")
            print("=" * 70)
            print(f"Fecha: {self.resultados['fecha_auditoria']}")
            print(f"URL: {self.resultados['url']}")
            print(f"Endpoint: {self.resultados['endpoint']}")
            
            # Ejecutar todas las verificaciones
            self.verificar_conectividad()
            self.verificar_conexion_bd()
            self.verificar_estructura_tabla()
            self.verificar_datos_bd()
            self.verificar_endpoint_backend()
            self.verificar_rendimiento()
            self.verificar_indices()
            self.verificar_validaciones()
            self.verificar_endpoint_api()
            
            # Generar reporte
            return self.generar_reporte()

    if __name__ == "__main__":
        auditoria = AuditoriaIntegralPrestamos()
        exito = auditoria.ejecutar_auditoria_completa()
        sys.exit(0 if exito else 1)

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de tener todas las dependencias instaladas:")
    print("  pip install sqlalchemy requests beautifulsoup4")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
