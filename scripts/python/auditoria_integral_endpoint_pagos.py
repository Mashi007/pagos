"""
Auditoría Integral del Endpoint /pagos
Verifica: seguridad, rendimiento, estructura de datos, errores, conectividad y más
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urljoin

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from sqlalchemy import create_engine, text, func
    from sqlalchemy.orm import sessionmaker, joinedload
    from app.core.config import settings
    from app.db.session import SessionLocal, engine, get_db, test_connection
    from app.models.pago import Pago
    from app.models.cliente import Cliente
    from app.models.prestamo import Prestamo
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

    class AuditoriaIntegralPagos:
        def __init__(self):
            self.resultados = {
                "fecha_auditoria": datetime.now().isoformat(),
                "endpoint": "https://rapicredit.onrender.com/pagos",
                "endpoint_api": "https://rapicredit.onrender.com/api/v1/pagos",
                "verificaciones": {}
            }
            self.errores = []
            self.advertencias = []
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            })

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
            """Verifica estructura de la tabla pagos"""
            print("\n" + "=" * 70)
            print("2. VERIFICACIÓN: Estructura de Tabla 'pagos'")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    # Verificar si la tabla existe
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'pagos'
                        )
                    """))
                    existe = result.scalar()
                    
                    if not existe:
                        print("   ❌ Tabla 'pagos' NO existe")
                        self.resultados["verificaciones"]["estructura_tabla"] = {
                            "estado": "error",
                            "mensaje": "La tabla no existe"
                        }
                        self.errores.append("Tabla 'pagos' no existe en la base de datos")
                        return False
                    
                    if settings.DATABASE_URL.startswith("postgresql"):
                        result = db.execute(text("""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns
                            WHERE table_name = 'pagos'
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
                        columnas_criticas = ['id', 'cedula', 'fecha_pago', 'monto_pagado', 
                                            'numero_documento', 'estado', 'activo', 'usuario_registro']
                        columnas_opcionales = ['cliente_id', 'prestamo_id', 'numero_cuota', 
                                              'institucion_bancaria', 'conciliado', 'notas']
                        
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
                return False

        def verificar_datos_bd(self) -> bool:
            """Verifica datos en la base de datos"""
            print("\n" + "=" * 70)
            print("3. VERIFICACIÓN: Datos en Base de Datos")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    # Verificar si la tabla existe primero
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'pagos'
                        )
                    """))
                    existe = result.scalar()
                    
                    if not existe:
                        print("   ⚠️  Tabla 'pagos' no existe - No hay datos para verificar")
                        self.resultados["verificaciones"]["datos_bd"] = {
                            "estado": "advertencia",
                            "mensaje": "Tabla no existe",
                            "total": 0
                        }
                        return True
                    
                    # Contar total
                    total = db.query(func.count(Pago.id)).scalar()
                    print(f"   ✅ Total de pagos: {total}")
                    
                    if total == 0:
                        print("   ⚠️  No hay pagos en la base de datos")
                        self.resultados["verificaciones"]["datos_bd"] = {
                            "estado": "advertencia",
                            "mensaje": "No hay datos",
                            "total": 0
                        }
                        return True
                    
                    # Contar por estado
                    estados = db.query(Pago.estado, func.count(Pago.id)).group_by(Pago.estado).all()
                    estados_dict = {estado: count for estado, count in estados}
                    
                    print("   ✅ Distribución por estado:")
                    for estado, count in estados_dict.items():
                        print(f"      - {estado}: {count}")
                    
                    # Contar por conciliación
                    conciliados = db.query(func.count(Pago.id)).filter(Pago.conciliado == True).scalar()
                    no_conciliados = total - conciliados
                    
                    print(f"   ✅ Pagos conciliados: {conciliados}")
                    print(f"   ✅ Pagos no conciliados: {no_conciliados}")
                    
                    # Contar activos vs inactivos
                    activos = db.query(func.count(Pago.id)).filter(Pago.activo == True).scalar()
                    inactivos = total - activos
                    
                    print(f"   ✅ Pagos activos: {activos}")
                    print(f"   ✅ Pagos inactivos: {inactivos}")
                    
                    # Verificar integridad de datos
                    sin_monto = db.query(Pago).filter(
                        (Pago.monto_pagado == None) | (Pago.monto_pagado <= 0)
                    ).count()
                    sin_cedula = db.query(Pago).filter(
                        (Pago.cedula == None) | (Pago.cedula == "")
                    ).count()
                    sin_numero_documento = db.query(Pago).filter(
                        (Pago.numero_documento == None) | (Pago.numero_documento == "")
                    ).count()
                    
                    if sin_monto > 0:
                        print(f"   ⚠️  Pagos sin monto válido: {sin_monto}")
                        self.advertencias.append(f"{sin_monto} pagos sin monto válido")
                    
                    if sin_cedula > 0:
                        print(f"   ⚠️  Pagos sin cédula: {sin_cedula}")
                        self.advertencias.append(f"{sin_cedula} pagos sin cédula")
                    
                    if sin_numero_documento > 0:
                        print(f"   ⚠️  Pagos sin número de documento: {sin_numero_documento}")
                        self.advertencias.append(f"{sin_numero_documento} pagos sin número de documento")
                    
                    # Verificar relaciones
                    con_cliente = db.query(Pago).filter(Pago.cliente_id != None).count()
                    sin_cliente = total - con_cliente
                    con_prestamo = db.query(Pago).filter(Pago.prestamo_id != None).count()
                    sin_prestamo = total - con_prestamo
                    
                    print(f"   ✅ Pagos con cliente_id: {con_cliente}")
                    print(f"   ✅ Pagos sin cliente_id: {sin_cliente}")
                    print(f"   ✅ Pagos con prestamo_id: {con_prestamo}")
                    print(f"   ✅ Pagos sin prestamo_id: {sin_prestamo}")
                    
                    # Obtener muestra de datos
                    muestra = db.query(Pago).limit(5).all()
                    muestra_serializada = []
                    for pago in muestra:
                        try:
                            pago_dict = {
                                "id": pago.id,
                                "cedula": pago.cedula,
                                "monto_pagado": float(pago.monto_pagado) if pago.monto_pagado else None,
                                "fecha_pago": pago.fecha_pago.isoformat() if pago.fecha_pago else None,
                                "estado": pago.estado,
                                "conciliado": pago.conciliado
                            }
                            muestra_serializada.append(pago_dict)
                        except Exception as e:
                            print(f"   ⚠️  Error serializando pago {pago.id}: {e}")
                    
                    self.resultados["verificaciones"]["datos_bd"] = {
                        "estado": "exitoso",
                        "total": total,
                        "por_estado": estados_dict,
                        "conciliados": conciliados,
                        "no_conciliados": no_conciliados,
                        "activos": activos,
                        "inactivos": inactivos,
                        "sin_monto": sin_monto,
                        "sin_cedula": sin_cedula,
                        "sin_numero_documento": sin_numero_documento,
                        "con_cliente": con_cliente,
                        "sin_cliente": sin_cliente,
                        "con_prestamo": con_prestamo,
                        "sin_prestamo": sin_prestamo,
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
                return False

        def verificar_endpoint_backend(self) -> bool:
            """Verifica el endpoint directamente desde el backend"""
            print("\n" + "=" * 70)
            print("4. VERIFICACIÓN: Endpoint Backend (Local)")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    # Verificar si la tabla existe
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'pagos'
                        )
                    """))
                    existe = result.scalar()
                    
                    if not existe:
                        print("   ⚠️  Tabla no existe - No se pueden ejecutar queries")
                        self.resultados["verificaciones"]["endpoint_backend"] = {
                            "estado": "advertencia",
                            "mensaje": "Tabla no existe"
                        }
                        return True
                    
                    resultados_pruebas = []
                    
                    # Prueba 1: Query básica
                    try:
                        start_time = time.time()
                        query = db.query(Pago)
                        total = query.count()
                        pagos = query.order_by(Pago.id.desc()).limit(20).all()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query básica: {len(pagos)} pagos en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_basica",
                            "tiempo_ms": tiempo,
                            "registros": len(pagos),
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
                        query = db.query(Pago).filter(Pago.estado == "PAGADO")
                        pagados = query.limit(20).all()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query con filtro de estado: {len(pagados)} pagados en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_con_filtro_estado",
                            "tiempo_ms": tiempo,
                            "registros": len(pagados),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ❌ Error en query con filtro: {e}")
                        resultados_pruebas.append({
                            "test": "query_con_filtro_estado",
                            "error": str(e),
                            "exitoso": False
                        })
                    
                    # Prueba 3: Con joinedload de relaciones (solo cliente, sin prestamo por posibles problemas de schema)
                    try:
                        start_time = time.time()
                        query = db.query(Pago).options(joinedload(Pago.cliente))
                        pagos_relaciones = query.limit(20).all()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query con relación cliente: {len(pagos_relaciones)} pagos en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_con_relacion_cliente",
                            "tiempo_ms": tiempo,
                            "registros": len(pagos_relaciones),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ⚠️  Error en query con relación cliente: {e}")
                        resultados_pruebas.append({
                            "test": "query_con_relacion_cliente",
                            "error": str(e),
                            "exitoso": False,
                            "advertencia": "Posible desajuste entre modelo y BD"
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
                    # Verificar si la tabla existe
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'pagos'
                        )
                    """))
                    existe = result.scalar()
                    
                    if not existe:
                        print("   ⚠️  Tabla no existe - No se pueden ejecutar pruebas de rendimiento")
                        self.resultados["verificaciones"]["rendimiento"] = {
                            "estado": "advertencia",
                            "mensaje": "Tabla no existe"
                        }
                        return True
                    
                    resultados_rendimiento = []
                    
                    # Test 1: COUNT sin filtros
                    start_time = time.time()
                    total = db.query(func.count(Pago.id)).scalar()
                    tiempo_count = (time.time() - start_time) * 1000
                    print(f"   ✅ COUNT total: {tiempo_count:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "count_total",
                        "tiempo_ms": tiempo_count,
                        "aceptable": tiempo_count < 1000
                    })
                    
                    # Test 2: Query con paginación
                    start_time = time.time()
                    pagos = db.query(Pago).order_by(Pago.id.desc()).limit(20).offset(0).all()
                    tiempo_query = (time.time() - start_time) * 1000
                    print(f"   ✅ Query paginada (20 registros): {tiempo_query:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_paginada_20",
                        "tiempo_ms": tiempo_query,
                        "aceptable": tiempo_query < 500
                    })
                    
                    # Test 3: Query con filtros
                    start_time = time.time()
                    pagados = db.query(Pago).filter(Pago.estado == "PAGADO").limit(20).all()
                    tiempo_filtro = (time.time() - start_time) * 1000
                    print(f"   ✅ Query con filtro: {tiempo_filtro:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_con_filtro",
                        "tiempo_ms": tiempo_filtro,
                        "aceptable": tiempo_filtro < 500
                    })
                    
                    # Test 4: Query con relación cliente (evitar prestamo por posibles problemas de schema)
                    try:
                        start_time = time.time()
                        pagos_relaciones = db.query(Pago).options(
                            joinedload(Pago.cliente)
                        ).limit(10).all()
                        tiempo_relaciones = (time.time() - start_time) * 1000
                        print(f"   ✅ Query con relación cliente (10 registros): {tiempo_relaciones:.2f}ms")
                        resultados_rendimiento.append({
                            "operacion": "query_con_relacion_cliente_10",
                            "tiempo_ms": tiempo_relaciones,
                            "aceptable": tiempo_relaciones < 1000
                        })
                    except Exception as e:
                        print(f"   ⚠️  Error en query con relaciones: {e}")
                        resultados_rendimiento.append({
                            "operacion": "query_con_relacion_cliente_10",
                            "tiempo_ms": None,
                            "aceptable": False,
                            "error": "Error al ejecutar query con relaciones"
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
                    # Verificar si la tabla existe
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'pagos'
                        )
                    """))
                    existe = result.scalar()
                    
                    if not existe:
                        print("   ⚠️  Tabla no existe - No hay índices para verificar")
                        self.resultados["verificaciones"]["indices"] = {
                            "estado": "advertencia",
                            "mensaje": "Tabla no existe"
                        }
                        return True
                    
                    if settings.DATABASE_URL.startswith("postgresql"):
                        result = db.execute(text("""
                            SELECT
                                indexname,
                                indexdef
                            FROM pg_indexes
                            WHERE tablename = 'pagos'
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
                        indices_criticos = ['pagos_pkey', 'ix_pagos_id', 'ix_pagos_cedula', 
                                         'ix_pagos_cliente_id', 'ix_pagos_prestamo_id',
                                         'ix_pagos_estado', 'ix_pagos_fecha_registro',
                                         'ix_pagos_numero_documento']
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
                    # Verificar si la tabla existe
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'pagos'
                        )
                    """))
                    existe = result.scalar()
                    
                    if not existe:
                        print("   ⚠️  Tabla no existe - No hay datos para validar")
                        self.resultados["verificaciones"]["validaciones"] = {
                            "estado": "advertencia",
                            "mensaje": "Tabla no existe"
                        }
                        return True
                    
                    problemas = []
                    
                    # Verificar estados válidos
                    estados_validos = ['PAGADO', 'PENDIENTE', 'PARCIAL', 'ADELANTADO']
                    result = db.execute(text("""
                        SELECT estado, COUNT(*) as count
                        FROM pagos
                        GROUP BY estado
                    """))
                    estados_encontrados = {row[0]: row[1] for row in result.fetchall()}
                    estados_invalidos = [e for e in estados_encontrados.keys() if e not in estados_validos]
                    if estados_invalidos:
                        print(f"   ⚠️  Estados inválidos encontrados: {estados_invalidos}")
                        problemas.append(f"Estados inválidos: {', '.join(estados_invalidos)}")
                    
                    # Verificar fechas futuras en fecha_pago
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM pagos
                        WHERE fecha_pago > CURRENT_TIMESTAMP
                    """))
                    fechas_futuras = result.scalar()
                    if fechas_futuras > 0:
                        print(f"   ⚠️  Fechas de pago futuras: {fechas_futuras}")
                        problemas.append(f"{fechas_futuras} fechas futuras")
                    
                    # Verificar clientes huérfanos
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM pagos p
                        LEFT JOIN clientes c ON p.cliente_id = c.id
                        WHERE p.cliente_id IS NOT NULL AND c.id IS NULL
                    """))
                    clientes_huerfanos = result.scalar()
                    if clientes_huerfanos > 0:
                        print(f"   ⚠️  Pagos con cliente_id inexistente: {clientes_huerfanos}")
                        problemas.append(f"{clientes_huerfanos} pagos con cliente_id inexistente")
                    
                    # Verificar préstamos huérfanos
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM pagos p
                        LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
                        WHERE p.prestamo_id IS NOT NULL AND pr.id IS NULL
                    """))
                    prestamos_huerfanos = result.scalar()
                    if prestamos_huerfanos > 0:
                        print(f"   ⚠️  Pagos con prestamo_id inexistente: {prestamos_huerfanos}")
                        problemas.append(f"{prestamos_huerfanos} pagos con prestamo_id inexistente")
                    
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

        def verificar_conectividad_produccion(self) -> bool:
            """Verifica conectividad del endpoint en producción"""
            print("\n" + "=" * 70)
            print("8. VERIFICACIÓN: Conectividad Endpoint en Producción")
            print("=" * 70)
            
            resultados_conectividad = {}
            
            # Verificar endpoint principal /pagos (frontend)
            try:
                url = urljoin(BASE_URL, "/pagos")
                start_time = time.time()
                response = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                tiempo_respuesta = (time.time() - start_time) * 1000
                
                resultados_conectividad["endpoint_pagos"] = {
                    "url": url,
                    "status_code": response.status_code,
                    "tiempo_respuesta_ms": round(tiempo_respuesta, 2),
                    "accesible": response.status_code in [200, 301, 302, 401, 403],
                    "tipo": "frontend"
                }
                
                if response.status_code in [200, 301, 302]:
                    print(f"   ✅ Endpoint /pagos accesible - Status: {response.status_code} ({tiempo_respuesta:.2f}ms)")
                elif response.status_code in [401, 403]:
                    print(f"   ⚠️  Endpoint /pagos requiere autenticación - Status: {response.status_code}")
                else:
                    print(f"   ❌ Endpoint /pagos no accesible - Status: {response.status_code}")
            except requests.exceptions.Timeout:
                resultados_conectividad["endpoint_pagos"] = {
                    "accesible": False,
                    "error": "Timeout",
                    "tipo": "frontend"
                }
                print(f"   ❌ Timeout al conectar a /pagos")
            except Exception as e:
                resultados_conectividad["endpoint_pagos"] = {
                    "accesible": False,
                    "error": str(e),
                    "tipo": "frontend"
                }
                print(f"   ❌ Error conectando a /pagos: {e}")
            
            # Verificar endpoint API /api/v1/pagos (requiere autenticación)
            try:
                url = urljoin(BASE_URL, "/api/v1/pagos")
                start_time = time.time()
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                tiempo_respuesta = (time.time() - start_time) * 1000
                
                resultados_conectividad["endpoint_api_pagos"] = {
                    "url": url,
                    "status_code": response.status_code,
                    "tiempo_respuesta_ms": round(tiempo_respuesta, 2),
                    "accesible": response.status_code in [200, 401, 403],
                    "tipo": "api",
                    "requiere_auth": response.status_code in [401, 403]
                }
                
                if response.status_code == 200:
                    print(f"   ✅ Endpoint API /api/v1/pagos accesible - Status: {response.status_code} ({tiempo_respuesta:.2f}ms)")
                    try:
                        data = response.json()
                        resultados_conectividad["endpoint_api_pagos"]["tiene_datos"] = isinstance(data, dict) and "items" in data
                    except:
                        pass
                elif response.status_code in [401, 403]:
                    print(f"   ✅ Endpoint API /api/v1/pagos requiere autenticación (esperado) - Status: {response.status_code}")
                elif response.status_code == 404:
                    print(f"   ⚠️  Endpoint API /api/v1/pagos no encontrado - Status: {response.status_code}")
                else:
                    print(f"   ❌ Endpoint API /api/v1/pagos no accesible - Status: {response.status_code}")
            except requests.exceptions.Timeout:
                resultados_conectividad["endpoint_api_pagos"] = {
                    "accesible": False,
                    "error": "Timeout",
                    "tipo": "api"
                }
                print(f"   ❌ Timeout al conectar a /api/v1/pagos")
            except Exception as e:
                resultados_conectividad["endpoint_api_pagos"] = {
                    "accesible": False,
                    "error": str(e),
                    "tipo": "api"
                }
                print(f"   ❌ Error conectando a /api/v1/pagos: {e}")
            
            # Verificar endpoint de health de pagos
            try:
                url = urljoin(BASE_URL, "/api/v1/pagos/health")
                start_time = time.time()
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                tiempo_respuesta = (time.time() - start_time) * 1000
                
                resultados_conectividad["endpoint_health"] = {
                    "url": url,
                    "status_code": response.status_code,
                    "tiempo_respuesta_ms": round(tiempo_respuesta, 2),
                    "accesible": response.status_code == 200,
                    "tipo": "health"
                }
                
                if response.status_code == 200:
                    print(f"   ✅ Endpoint Health /api/v1/pagos/health accesible - Status: {response.status_code} ({tiempo_respuesta:.2f}ms)")
                    try:
                        data = response.json()
                        resultados_conectividad["endpoint_health"]["datos"] = data
                    except:
                        pass
                else:
                    print(f"   ⚠️  Endpoint Health /api/v1/pagos/health - Status: {response.status_code}")
            except Exception as e:
                resultados_conectividad["endpoint_health"] = {
                    "accesible": False,
                    "error": str(e),
                    "tipo": "health"
                }
                print(f"   ⚠️  Error conectando a /api/v1/pagos/health: {e}")
            
            self.resultados["verificaciones"]["conectividad_produccion"] = resultados_conectividad
            
            # Determinar estado general (considerar 401/403 como éxito ya que indica que el endpoint existe)
            endpoints_funcionales = sum(
                1 for r in resultados_conectividad.values()
                if r.get("accesible", False) or r.get("requiere_auth", False)
            )
            total_endpoints = len(resultados_conectividad)
            
            self.resultados["verificaciones"]["conectividad_produccion"]["estado"] = (
                "exitoso" if endpoints_funcionales == total_endpoints else "parcial"
            )
            self.resultados["verificaciones"]["conectividad_produccion"]["endpoints_funcionales"] = endpoints_funcionales
            self.resultados["verificaciones"]["conectividad_produccion"]["total_endpoints"] = total_endpoints
            
            return True

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
            
            total = len([v for v in self.resultados["verificaciones"].values() if isinstance(v, dict)])
            
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
            reporte_path = Path(__file__).parent.parent.parent / "AUDITORIA_PAGOS.json"
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
            """Genera reporte en formato Markdown"""
            ruta_md = Path(__file__).parent.parent.parent / "AUDITORIA_INTEGRAL_PAGOS.md"
            
            with open(ruta_md, 'w', encoding='utf-8') as f:
                f.write("# 🔍 AUDITORÍA INTEGRAL DEL ENDPOINT /pagos\n\n")
                f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Endpoint:** {self.resultados['endpoint']}\n")
                f.write(f"**Endpoint API:** {self.resultados['endpoint_api']}\n\n")
                
                # Resumen ejecutivo
                exitosas = sum(1 for v in self.resultados["verificaciones"].values() 
                              if isinstance(v, dict) and v.get("estado") == "exitoso")
                total = len([v for v in self.resultados["verificaciones"].values() if isinstance(v, dict)])
                
                f.write("## 📊 RESUMEN EJECUTIVO\n\n")
                f.write(f"**Verificaciones exitosas:** {exitosas}/{total}\n\n")
                
                # Detalles por verificación
                f.write("## 📋 DETALLES DE VERIFICACIONES\n\n")
                for nombre, resultado in self.resultados["verificaciones"].items():
                    if isinstance(resultado, dict):
                        estado_emoji = {
                            "exitoso": "✅",
                            "parcial": "⚠️",
                            "advertencia": "⚠️",
                            "error": "❌"
                        }.get(resultado.get("estado"), "❓")
                        
                        f.write(f"### {estado_emoji} {nombre.replace('_', ' ').title()}\n\n")
                        f.write(f"**Estado:** {resultado.get('estado', 'N/A')}\n\n")
                        
                        if resultado.get("mensaje"):
                            f.write(f"**Mensaje:** {resultado['mensaje']}\n\n")
                
                # Advertencias y errores
                if self.advertencias:
                    f.write("## ⚠️ ADVERTENCIAS\n\n")
                    for adv in self.advertencias:
                        f.write(f"- {adv}\n")
                    f.write("\n")
                
                if self.errores:
                    f.write("## ❌ ERRORES\n\n")
                    for err in self.errores:
                        f.write(f"- {err}\n")
                    f.write("\n")
            
            print(f"[INFO] Reporte Markdown guardado en: {ruta_md}")

        def ejecutar_auditoria_completa(self):
            """Ejecuta todas las verificaciones"""
            print("=" * 70)
            print("AUDITORÍA INTEGRAL: Endpoint /pagos")
            print("=" * 70)
            print(f"Fecha: {self.resultados['fecha_auditoria']}")
            print(f"Endpoint: {self.resultados['endpoint']}")
            print(f"Endpoint API: {self.resultados['endpoint_api']}")
            
            # Ejecutar todas las verificaciones
            self.verificar_conexion_bd()
            self.verificar_estructura_tabla()
            self.verificar_datos_bd()
            self.verificar_endpoint_backend()
            self.verificar_rendimiento()
            self.verificar_indices()
            self.verificar_validaciones()
            self.verificar_conectividad_produccion()
            
            # Generar reporte
            return self.generar_reporte()

    if __name__ == "__main__":
        auditoria = AuditoriaIntegralPagos()
        exito = auditoria.ejecutar_auditoria_completa()
        sys.exit(0 if exito else 1)

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de tener todas las dependencias instaladas:")
    print("  pip install sqlalchemy requests")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
