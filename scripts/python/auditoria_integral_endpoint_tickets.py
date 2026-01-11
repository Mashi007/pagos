"""
Auditoría Integral del Endpoint /tickets
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
    from app.models.ticket import Ticket
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

    class AuditoriaIntegralTickets:
        def __init__(self):
            self.resultados = {
                "fecha_auditoria": datetime.now().isoformat(),
                "endpoint": "https://rapicredit.onrender.com/api/v1/tickets",
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
            """Verifica estructura de la tabla tickets"""
            print("\n" + "=" * 70)
            print("2. VERIFICACIÓN: Estructura de Tabla 'tickets'")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    # Verificar si la tabla existe
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'tickets'
                        )
                    """))
                    existe = result.scalar()
                    
                    if not existe:
                        print("   ⚠️  Tabla 'tickets' NO existe")
                        self.resultados["verificaciones"]["estructura_tabla"] = {
                            "estado": "advertencia",
                            "mensaje": "La tabla no existe. Puede crearse automáticamente por el endpoint."
                        }
                        return True  # No es un error crítico, el endpoint puede crear la tabla
                    
                    if settings.DATABASE_URL.startswith("postgresql"):
                        result = db.execute(text("""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns
                            WHERE table_name = 'tickets'
                            ORDER BY ordinal_position
                        """))
                        columnas = result.fetchall()
                        
                        estructura = {}
                        for col in columnas:
                            estructura[col[0]] = {
                                "tipo": col[1],
                                "nullable": col[2] == "YES",
                                "default": str(col[3]) if col[3] else None
                            }
                        
                        print(f"   ✅ Columnas encontradas: {len(columnas)}")
                        for nombre, info in estructura.items():
                            nullable_str = "NULL" if info['nullable'] else "NOT NULL"
                            print(f"      - {nombre}: {info['tipo']} ({nullable_str})")
                        
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
                    # Verificar si la tabla existe primero
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'tickets'
                        )
                    """))
                    existe = result.scalar()
                    
                    if not existe:
                        print("   ⚠️  Tabla 'tickets' no existe - No hay datos para verificar")
                        self.resultados["verificaciones"]["datos_bd"] = {
                            "estado": "advertencia",
                            "mensaje": "Tabla no existe",
                            "total": 0
                        }
                        return True
                    
                    # Contar total
                    total = db.query(func.count(Ticket.id)).scalar()
                    print(f"   ✅ Total de tickets: {total}")
                    
                    if total == 0:
                        print("   ⚠️  No hay tickets en la base de datos")
                        self.resultados["verificaciones"]["datos_bd"] = {
                            "estado": "advertencia",
                            "mensaje": "No hay datos",
                            "total": 0
                        }
                        return True
                    
                    # Contar por estado
                    estados = db.query(Ticket.estado, func.count(Ticket.id)).group_by(Ticket.estado).all()
                    estados_dict = {estado: count for estado, count in estados}
                    
                    print("   ✅ Distribución por estado:")
                    for estado, count in estados_dict.items():
                        print(f"      - {estado}: {count}")
                    
                    # Contar por prioridad
                    prioridades = db.query(Ticket.prioridad, func.count(Ticket.id)).group_by(Ticket.prioridad).all()
                    prioridades_dict = {prioridad: count for prioridad, count in prioridades}
                    
                    print("   ✅ Distribución por prioridad:")
                    for prioridad, count in prioridades_dict.items():
                        print(f"      - {prioridad}: {count}")
                    
                    # Contar por tipo
                    tipos = db.query(Ticket.tipo, func.count(Ticket.id)).group_by(Ticket.tipo).all()
                    tipos_dict = {tipo: count for tipo, count in tipos}
                    
                    print("   ✅ Distribución por tipo:")
                    for tipo, count in tipos_dict.items():
                        print(f"      - {tipo}: {count}")
                    
                    # Verificar integridad de datos
                    sin_titulo = db.query(Ticket).filter(
                        (Ticket.titulo == None) | (Ticket.titulo == "")
                    ).count()
                    sin_descripcion = db.query(Ticket).filter(
                        (Ticket.descripcion == None) | (Ticket.descripcion == "")
                    ).count()
                    
                    if sin_titulo > 0:
                        print(f"   ⚠️  Tickets sin título: {sin_titulo}")
                        self.advertencias.append(f"{sin_titulo} tickets sin título")
                    
                    if sin_descripcion > 0:
                        print(f"   ⚠️  Tickets sin descripción: {sin_descripcion}")
                        self.advertencias.append(f"{sin_descripcion} tickets sin descripción")
                    
                    # Verificar relaciones
                    con_cliente = db.query(Ticket).filter(Ticket.cliente_id != None).count()
                    sin_cliente = total - con_cliente
                    
                    print(f"   ✅ Tickets con cliente: {con_cliente}")
                    print(f"   ✅ Tickets sin cliente: {sin_cliente}")
                    
                    # Obtener muestra de datos
                    muestra = db.query(Ticket).limit(5).all()
                    muestra_serializada = []
                    for ticket in muestra:
                        try:
                            ticket_dict = ticket.to_dict()
                            muestra_serializada.append(ticket_dict)
                        except Exception as e:
                            print(f"   ⚠️  Error serializando ticket {ticket.id}: {e}")
                    
                    self.resultados["verificaciones"]["datos_bd"] = {
                        "estado": "exitoso",
                        "total": total,
                        "por_estado": estados_dict,
                        "por_prioridad": prioridades_dict,
                        "por_tipo": tipos_dict,
                        "sin_titulo": sin_titulo,
                        "sin_descripcion": sin_descripcion,
                        "con_cliente": con_cliente,
                        "sin_cliente": sin_cliente,
                        "muestra": muestra_serializada[:3]  # Solo primeros 3
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
                            AND table_name = 'tickets'
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
                    
                    # Prueba 1: Query básica con joinedload
                    try:
                        from sqlalchemy.orm import joinedload
                        start_time = time.time()
                        query = db.query(Ticket).options(joinedload(Ticket.cliente))
                        total = query.count()
                        tickets = query.order_by(Ticket.creado_en.desc()).limit(20).all()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query básica con joinedload: {len(tickets)} tickets en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_basica_joinedload",
                            "tiempo_ms": tiempo,
                            "registros": len(tickets),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ❌ Error en query básica: {e}")
                        resultados_pruebas.append({
                            "test": "query_basica_joinedload",
                            "error": str(e),
                            "exitoso": False
                        })
                    
                    # Prueba 2: Con filtro de estado
                    try:
                        start_time = time.time()
                        query = db.query(Ticket).options(joinedload(Ticket.cliente)).filter(Ticket.estado == "abierto")
                        abiertos = query.limit(20).all()
                        tiempo = (time.time() - start_time) * 1000
                        
                        print(f"   ✅ Query con filtro de estado: {len(abiertos)} abiertos en {tiempo:.2f}ms")
                        resultados_pruebas.append({
                            "test": "query_con_filtro_estado",
                            "tiempo_ms": tiempo,
                            "registros": len(abiertos),
                            "exitoso": True
                        })
                    except Exception as e:
                        print(f"   ❌ Error en query con filtro: {e}")
                        resultados_pruebas.append({
                            "test": "query_con_filtro_estado",
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
                    # Verificar si la tabla existe
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'tickets'
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
                    from sqlalchemy.orm import joinedload
                    
                    # Test 1: COUNT sin filtros
                    start_time = time.time()
                    total = db.query(func.count(Ticket.id)).scalar()
                    tiempo_count = (time.time() - start_time) * 1000
                    print(f"   ✅ COUNT total: {tiempo_count:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "count_total",
                        "tiempo_ms": tiempo_count,
                        "aceptable": tiempo_count < 1000
                    })
                    
                    # Test 2: Query con paginación y joinedload
                    start_time = time.time()
                    tickets = db.query(Ticket).options(joinedload(Ticket.cliente)).order_by(Ticket.creado_en.desc()).limit(20).offset(0).all()
                    tiempo_query = (time.time() - start_time) * 1000
                    print(f"   ✅ Query paginada con joinedload (20 registros): {tiempo_query:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_paginada_joinedload_20",
                        "tiempo_ms": tiempo_query,
                        "aceptable": tiempo_query < 500
                    })
                    
                    # Test 3: Query con filtros
                    start_time = time.time()
                    abiertos = db.query(Ticket).options(joinedload(Ticket.cliente)).filter(Ticket.estado == "abierto").limit(20).all()
                    tiempo_filtro = (time.time() - start_time) * 1000
                    print(f"   ✅ Query con filtro: {tiempo_filtro:.2f}ms")
                    resultados_rendimiento.append({
                        "operacion": "query_con_filtro",
                        "tiempo_ms": tiempo_filtro,
                        "aceptable": tiempo_filtro < 500
                    })
                    
                    # Test 4: Serialización
                    start_time = time.time()
                    tickets_serializados = []
                    for ticket in tickets[:10]:
                        try:
                            ticket_dict = ticket.to_dict()
                            tickets_serializados.append(ticket_dict)
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
                    # Verificar si la tabla existe
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'tickets'
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
                            WHERE tablename = 'tickets'
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
                        indices_criticos = ['tickets_pkey', 'ix_tickets_id', 'ix_tickets_titulo', 
                                         'ix_tickets_cliente_id', 'ix_tickets_estado', 
                                         'ix_tickets_prioridad', 'ix_tickets_tipo', 'ix_tickets_creado_en']
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
                            AND table_name = 'tickets'
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
                    estados_validos = ['abierto', 'en_proceso', 'resuelto', 'cerrado']
                    result = db.execute(text("""
                        SELECT estado, COUNT(*) as count
                        FROM tickets
                        GROUP BY estado
                    """))
                    estados_encontrados = {row[0]: row[1] for row in result.fetchall()}
                    estados_invalidos = [e for e in estados_encontrados.keys() if e not in estados_validos]
                    if estados_invalidos:
                        print(f"   ⚠️  Estados inválidos encontrados: {estados_invalidos}")
                        problemas.append(f"Estados inválidos: {', '.join(estados_invalidos)}")
                    
                    # Verificar prioridades válidas
                    prioridades_validas = ['baja', 'media', 'urgente']
                    result = db.execute(text("""
                        SELECT prioridad, COUNT(*) as count
                        FROM tickets
                        GROUP BY prioridad
                    """))
                    prioridades_encontradas = {row[0]: row[1] for row in result.fetchall()}
                    prioridades_invalidas = [p for p in prioridades_encontradas.keys() if p not in prioridades_validas]
                    if prioridades_invalidas:
                        print(f"   ⚠️  Prioridades inválidas encontradas: {prioridades_invalidas}")
                        problemas.append(f"Prioridades inválidas: {', '.join(prioridades_invalidas)}")
                    
                    # Verificar fechas futuras en creado_en
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM tickets
                        WHERE creado_en > CURRENT_TIMESTAMP
                    """))
                    fechas_futuras = result.scalar()
                    if fechas_futuras > 0:
                        print(f"   ⚠️  Fechas de creación futuras: {fechas_futuras}")
                        problemas.append(f"{fechas_futuras} fechas futuras")
                    
                    # Verificar clientes huérfanos (cliente_id que no existe)
                    result = db.execute(text("""
                        SELECT COUNT(*) 
                        FROM tickets t
                        LEFT JOIN clientes c ON t.cliente_id = c.id
                        WHERE t.cliente_id IS NOT NULL AND c.id IS NULL
                    """))
                    clientes_huerfanos = result.scalar()
                    if clientes_huerfanos > 0:
                        print(f"   ⚠️  Tickets con cliente_id inexistente: {clientes_huerfanos}")
                        problemas.append(f"{clientes_huerfanos} tickets con cliente_id inexistente")
                    
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
            reporte_path = Path(__file__).parent.parent.parent / "Documentos" / "Auditorias" / "AUDITORIA_TICKETS.json"
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
            
            return exitosas == total

        def ejecutar_auditoria_completa(self):
            """Ejecuta todas las verificaciones"""
            print("=" * 70)
            print("AUDITORÍA INTEGRAL: Endpoint /tickets")
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
        auditoria = AuditoriaIntegralTickets()
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
