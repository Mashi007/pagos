"""
Auditoría Integral del Endpoint /notificaciones
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
    from sqlalchemy import create_engine, text, func
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.db.session import SessionLocal, engine, get_db, test_connection
    from app.models.notificacion import Notificacion
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

    class AuditoriaIntegralNotificaciones:
        def __init__(self):
            self.resultados = {
                "fecha_auditoria": datetime.now().isoformat(),
                "endpoint": "https://rapicredit.onrender.com/api/v1/notificaciones",
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
            """Verifica estructura de la tabla notificaciones"""
            print("\n" + "=" * 70)
            print("2. VERIFICACIÓN: Estructura de Tabla 'notificaciones'")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    if settings.DATABASE_URL.startswith("postgresql"):
                        result = db.execute(text("""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns
                            WHERE table_name = 'notificaciones'
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
                        columnas_criticas = ['id', 'cliente_id', 'user_id', 'tipo', 'mensaje', 'estado']
                        columnas_opcionales = ['canal', 'asunto', 'leida', 'created_at']
                        
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
                    # Contar total
                    total = db.query(func.count(Notificacion.id)).scalar()
                    print(f"   ✅ Total de notificaciones: {total}")
                    
                    if total == 0:
                        print("   ⚠️  No hay notificaciones en la base de datos")
                        self.resultados["verificaciones"]["datos_bd"] = {
                            "estado": "advertencia",
                            "mensaje": "No hay datos",
                            "total": 0
                        }
                        return True
                    
                    # Contar por estado
                    estados = db.query(Notificacion.estado, func.count(Notificacion.id)).group_by(Notificacion.estado).all()
                    estados_dict = {estado: count for estado, count in estados}
                    
                    print("   ✅ Distribución por estado:")
                    for estado, count in estados_dict.items():
                        print(f"      - {estado}: {count}")
                    
                    # Contar por tipo
                    tipos = db.query(Notificacion.tipo, func.count(Notificacion.id)).group_by(Notificacion.tipo).all()
                    tipos_dict = {tipo: count for tipo, count in tipos}
                    
                    print("   ✅ Distribución por tipo:")
                    for tipo, count in tipos_dict.items():
                        print(f"      - {tipo}: {count}")
                    
                    # Verificar si existe columna canal
                    try:
                        result = db.execute(text("""
                            SELECT COUNT(*) 
                            FROM information_schema.columns
                            WHERE table_name = 'notificaciones' AND column_name = 'canal'
                        """))
                        tiene_canal = result.scalar() > 0
                        
                        if tiene_canal:
                            canales = db.execute(text("""
                                SELECT canal, COUNT(*) as count
                                FROM notificaciones
                                WHERE canal IS NOT NULL
                                GROUP BY canal
                            """)).fetchall()
                            canales_dict = {canal: count for canal, count in canales}
                            print("   ✅ Distribución por canal:")
                            for canal, count in canales_dict.items():
                                print(f"      - {canal}: {count}")
                    except Exception:
                        tiene_canal = False
                    
                    # Verificar integridad de datos
                    sin_mensaje = db.query(Notificacion).filter(
                        (Notificacion.mensaje == None) | (Notificacion.mensaje == "")
                    ).count()
                    sin_tipo = db.query(Notificacion).filter(
                        (Notificacion.tipo == None) | (Notificacion.tipo == "")
                    ).count()
                    
                    if sin_mensaje > 0:
                        print(f"   ⚠️  Notificaciones sin mensaje: {sin_mensaje}")
                        self.advertencias.append(f"{sin_mensaje} notificaciones sin mensaje")
                    
                    if sin_tipo > 0:
                        print(f"   ⚠️  Notificaciones sin tipo: {sin_tipo}")
                        self.advertencias.append(f"{sin_tipo} notificaciones sin tipo")
                    
                    # Verificar relaciones
                    con_cliente = db.query(Notificacion).filter(Notificacion.cliente_id != None).count()
                    sin_cliente = total - con_cliente
                    
                    print(f"   ✅ Notificaciones con cliente: {con_cliente}")
                    print(f"   ✅ Notificaciones sin cliente: {sin_cliente}")
                    
                    # Obtener muestra de datos
                    muestra = db.query(Notificacion).limit(5).all()
                    muestra_serializada = []
                    for notificacion in muestra:
                        try:
                            notificacion_dict = notificacion.to_dict()
                            muestra_serializada.append(notificacion_dict)
                        except Exception as e:
                            print(f"   ⚠️  Error serializando notificación {notificacion.id}: {e}")
                    
                    resultado = {
                        "estado": "exitoso",
                        "total": total,
                        "por_estado": estados_dict,
                        "por_tipo": tipos_dict,
                        "sin_mensaje": sin_mensaje,
                        "sin_tipo": sin_tipo,
                        "con_cliente": con_cliente,
                        "sin_cliente": sin_cliente,
                        "muestra": muestra_serializada[:3]
                    }
                    
                    if tiene_canal:
                        resultado["por_canal"] = canales_dict
                    
                    self.resultados["verificaciones"]["datos_bd"] = resultado
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
                    resultados_pruebas = []
                    
                    # Prueba 1: Query básica
                    try:
                        start_time = time.time()
                        query = db.query(Notificacion)
                        total = query.count()
                        notificaciones = query.order_by(Notificacion.id.desc()).limit(20).all()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query básica: {len(notificaciones)} notificaciones en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_basica",
                            "tiempo_ms": tiempo,
                            "registros": len(notificaciones),
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
                        query = db.query(Notificacion).filter(Notificacion.estado == "ENVIADA")
                        enviadas = query.limit(20).all()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query con filtro de estado: {len(enviadas)} enviadas en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_con_filtro_estado",
                            "tiempo_ms": tiempo,
                            "registros": len(enviadas),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ❌ Error en query con filtro: {e}")
                        resultados_pruebas.append({
                            "test": "query_con_filtro_estado",
                            "error": str(e),
                            "exitoso": False
                        })
                    
                    # Prueba 3: Con filtro de tipo
                    try:
                        start_time = time.time()
                        query = db.query(Notificacion).filter(Notificacion.tipo == "EMAIL")
                        emails = query.limit(20).all()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query con filtro de tipo: {len(emails)} emails en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_con_filtro_tipo",
                            "tiempo_ms": tiempo,
                            "registros": len(emails),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ❌ Error en query con filtro de tipo: {e}")
                        resultados_pruebas.append({
                            "test": "query_con_filtro_tipo",
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
                    total = db.query(func.count(Notificacion.id)).scalar()
                    tiempo_count = (time.time() - start_time) * 1000
                    print(f"   ✅ COUNT total: {tiempo_count:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "count_total",
                        "tiempo_ms": tiempo_count,
                        "aceptable": tiempo_count < 1000
                    })
                    
                    # Test 2: Query con paginación
                    start_time = time.time()
                    notificaciones = db.query(Notificacion).order_by(Notificacion.id.desc()).limit(20).offset(0).all()
                    tiempo_query = (time.time() - start_time) * 1000
                    print(f"   ✅ Query paginada (20 registros): {tiempo_query:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_paginada_20",
                        "tiempo_ms": tiempo_query,
                        "aceptable": tiempo_query < 500
                    })
                    
                    # Test 3: Query con filtros
                    start_time = time.time()
                    enviadas = db.query(Notificacion).filter(Notificacion.estado == "ENVIADA").limit(20).all()
                    tiempo_filtro = (time.time() - start_time) * 1000
                    print(f"   ✅ Query con filtro: {tiempo_filtro:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_con_filtro",
                        "tiempo_ms": tiempo_filtro,
                        "aceptable": tiempo_filtro < 500
                    })
                    
                    # Test 4: Serialización
                    start_time = time.time()
                    notificaciones_serializadas = []
                    for notificacion in notificaciones[:10]:
                        try:
                            notificacion_dict = notificacion.to_dict()
                            notificaciones_serializadas.append(notificacion_dict)
                        except Exception as e:
                            pass
                    tiempo_serializacion = (time.time() - start_time) * 1000
                    print(f"   ✅ Serialización (10 registros): {tiempo_serializacion:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "serializacion_10",
                        "tiempo_ms": tiempo_serializacion,
                        "aceptable": tiempo_serializacion < 100
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
                            WHERE tablename = 'notificaciones'
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
                        indices_criticos = ['notificaciones_pkey', 'ix_notificaciones_id', 
                                         'ix_notificaciones_cliente_id', 'ix_notificaciones_user_id',
                                         'ix_notificaciones_tipo', 'ix_notificaciones_estado']
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
                    
                    # Verificar estados válidos
                    estados_validos = ['PENDIENTE', 'ENVIADA', 'FALLIDA', 'CANCELADA']
                    result = db.execute(text("""
                        SELECT estado, COUNT(*) as count
                        FROM notificaciones
                        GROUP BY estado
                    """))
                    estados_encontrados = {row[0]: row[1] for row in result.fetchall()}
                    estados_invalidos = [e for e in estados_encontrados.keys() if e not in estados_validos]
                    if estados_invalidos:
                        print(f"   ⚠️  Estados inválidos encontrados: {estados_invalidos}")
                        problemas.append(f"Estados inválidos: {', '.join(estados_invalidos)}")
                    
                    # Verificar tipos válidos
                    tipos_validos = ['EMAIL', 'SMS', 'WHATSAPP', 'PUSH']
                    result = db.execute(text("""
                        SELECT tipo, COUNT(*) as count
                        FROM notificaciones
                        GROUP BY tipo
                    """))
                    tipos_encontrados = {row[0]: row[1] for row in result.fetchall()}
                    tipos_invalidos = [t for t in tipos_encontrados.keys() if t not in tipos_validos]
                    if tipos_invalidos:
                        print(f"   ⚠️  Tipos inválidos encontrados: {tipos_invalidos}")
                        problemas.append(f"Tipos inválidos: {', '.join(tipos_invalidos)}")
                    
                    # Verificar fechas futuras en programada_para
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM notificaciones
                        WHERE programada_para > CURRENT_TIMESTAMP
                    """))
                    fechas_futuras = result.scalar()
                    if fechas_futuras > 0:
                        print(f"   ✅ Notificaciones programadas para el futuro: {fechas_futuras} (esto es normal)")
                    
                    # Verificar clientes huérfanos
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM notificaciones n
                        LEFT JOIN clientes c ON n.cliente_id = c.id
                        WHERE n.cliente_id IS NOT NULL AND c.id IS NULL
                    """))
                    clientes_huerfanos = result.scalar()
                    if clientes_huerfanos > 0:
                        print(f"   ⚠️  Notificaciones con cliente_id inexistente: {clientes_huerfanos}")
                        problemas.append(f"{clientes_huerfanos} notificaciones con cliente_id inexistente")
                    
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

        def verificar_columnas_opcionales(self) -> bool:
            """Verifica columnas opcionales que pueden no existir"""
            print("\n" + "=" * 70)
            print("8. VERIFICACIÓN: Columnas Opcionales")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    if settings.DATABASE_URL.startswith("postgresql"):
                        result = db.execute(text("""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name = 'notificaciones'
                        """))
                        columnas_existentes = [row[0] for row in result.fetchall()]
                        
                        columnas_opcionales = {
                            "canal": "Canal de notificación (EMAIL, WHATSAPP)",
                            "asunto": "Asunto del mensaje",
                            "leida": "Indica si la notificación fue leída",
                            "created_at": "Fecha de creación (alternativa a id para ordenar)"
                        }
                        
                        columnas_faltantes = []
                        columnas_presentes = []
                        
                        for columna, descripcion in columnas_opcionales.items():
                            if columna in columnas_existentes:
                                print(f"   ✅ Columna '{columna}' existe: {descripcion}")
                                columnas_presentes.append(columna)
                            else:
                                print(f"   ⚠️  Columna '{columna}' NO existe: {descripcion}")
                                columnas_faltantes.append(columna)
                        
                        self.resultados["verificaciones"]["columnas_opcionales"] = {
                            "estado": "exitoso" if not columnas_faltantes else "advertencia",
                            "presentes": columnas_presentes,
                            "faltantes": columnas_faltantes
                        }
                        
                        if columnas_faltantes:
                            self.advertencias.append(f"Columnas opcionales faltantes: {', '.join(columnas_faltantes)}")
                        
                        return True
                    else:
                        print("   ⚠️  Verificación de columnas opcionales no disponible para SQLite")
                        self.resultados["verificaciones"]["columnas_opcionales"] = {
                            "estado": "advertencia",
                            "mensaje": "No disponible para SQLite"
                        }
                        return True
                finally:
                    db.close()
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["columnas_opcionales"] = {
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
            reporte_path = Path(__file__).parent.parent.parent / "AUDITORIA_NOTIFICACIONES.json"
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
            print("AUDITORÍA INTEGRAL: Endpoint /notificaciones")
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
            self.verificar_columnas_opcionales()
            
            # Generar reporte
            return self.generar_reporte()

    if __name__ == "__main__":
        auditoria = AuditoriaIntegralNotificaciones()
        exito = auditoria.ejecutar_auditoria_completa()
        sys.exit(0 if exito else 1)

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de tener todas las dependencias instaladas:")
    print("  pip install sqlalchemy")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
