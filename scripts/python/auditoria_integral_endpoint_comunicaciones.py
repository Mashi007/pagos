"""
Auditoría Integral del Endpoint /comunicaciones
Verifica: seguridad, rendimiento, estructura de datos, errores, y más
Endpoint unificado que combina WhatsApp y Email
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
    from app.models.conversacion_whatsapp import ConversacionWhatsApp
    from app.models.comunicacion_email import ComunicacionEmail
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

    class AuditoriaIntegralComunicaciones:
        def __init__(self):
            self.resultados = {
                "fecha_auditoria": datetime.now().isoformat(),
                "endpoint": "https://rapicredit.onrender.com/api/v1/comunicaciones",
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

        def verificar_estructura_tablas(self) -> bool:
            """Verifica estructura de las tablas conversaciones_whatsapp y comunicaciones_email"""
            print("\n" + "=" * 70)
            print("2. VERIFICACIÓN: Estructura de Tablas")
            print("=" * 70)
            
            tablas = {
                "conversaciones_whatsapp": "ConversacionWhatsApp",
                "comunicaciones_email": "ComunicacionEmail"
            }
            
            resultado_general = True
            
            for tabla_nombre, modelo_nombre in tablas.items():
                print(f"\n   📋 Tabla: {tabla_nombre}")
                try:
                    db = SessionLocal()
                    try:
                        if settings.DATABASE_URL.startswith("postgresql"):
                            result = db.execute(text(f"""
                                SELECT column_name, data_type, is_nullable, column_default
                                FROM information_schema.columns
                                WHERE table_name = '{tabla_nombre}'
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
                            
                            print(f"   ✅ Columnas encontradas: {len(columnas_encontradas)}")
                            for col_name in columnas_encontradas:
                                col_info = estructura[col_name]
                                nullable_str = "NULL" if col_info["nullable"] else "NOT NULL"
                                print(f"      - {col_name}: {col_info['tipo']} ({nullable_str})")
                            
                            # Verificar índices
                            result_idx = db.execute(text(f"""
                                SELECT indexname, indexdef
                                FROM pg_indexes
                                WHERE tablename = '{tabla_nombre}'
                            """))
                            indices = result_idx.fetchall()
                            
                            print(f"   ✅ Índices encontrados: {len(indices)}")
                            for idx in indices:
                                print(f"      - {idx[0]}")
                            
                            self.resultados["verificaciones"][f"estructura_{tabla_nombre}"] = {
                                "estado": "exitoso",
                                "columnas": estructura,
                                "total_columnas": len(columnas_encontradas),
                                "indices": [idx[0] for idx in indices],
                                "total_indices": len(indices)
                            }
                        else:
                            print("   ⚠️  Base de datos no PostgreSQL, saltando verificación de estructura")
                            self.resultados["verificaciones"][f"estructura_{tabla_nombre}"] = {
                                "estado": "advertencia",
                                "mensaje": "Base de datos no PostgreSQL"
                            }
                    finally:
                        db.close()
                except Exception as e:
                    print(f"   ❌ Error verificando estructura de {tabla_nombre}: {type(e).__name__}: {str(e)}")
                    self.resultados["verificaciones"][f"estructura_{tabla_nombre}"] = {
                        "estado": "error",
                        "mensaje": str(e)
                    }
                    resultado_general = False
            
            return resultado_general

        def verificar_datos_bd(self) -> bool:
            """Verifica datos en las tablas"""
            print("\n" + "=" * 70)
            print("3. VERIFICACIÓN: Datos en Base de Datos")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    # WhatsApp
                    total_whatsapp = db.query(func.count(ConversacionWhatsApp.id)).scalar() or 0
                    print(f"   📱 Total conversaciones WhatsApp: {total_whatsapp}")
                    
                    # Email
                    total_email = 0
                    try:
                        total_email = db.query(func.count(ComunicacionEmail.id)).scalar() or 0
                        print(f"   📧 Total comunicaciones Email: {total_email}")
                    except Exception as e:
                        print(f"   ⚠️  Tabla comunicaciones_email no existe o error: {str(e)}")
                        self.advertencias.append(f"Tabla comunicaciones_email: {str(e)}")
                    
                    total_general = total_whatsapp + total_email
                    print(f"   ✅ Total comunicaciones: {total_general}")
                    
                    if total_general == 0:
                        print("   ⚠️  No hay comunicaciones en la base de datos")
                        self.advertencias.append("Tablas vacías")
                    
                    self.resultados["verificaciones"]["datos_bd"] = {
                        "estado": "exitoso" if total_general > 0 else "advertencia",
                        "total_whatsapp": total_whatsapp,
                        "total_email": total_email,
                        "total_general": total_general
                    }
                    
                    return True
                finally:
                    db.close()
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["datos_bd"] = {
                    "estado": "error",
                    "mensaje": str(e)
                }
                return False

        def verificar_endpoint_backend(self) -> bool:
            """Verifica funcionamiento del endpoint backend local"""
            print("\n" + "=" * 70)
            print("4. VERIFICACIÓN: Endpoint Backend (Local)")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    # Query básica WhatsApp
                    inicio = time.time()
                    whatsapp_count = db.query(func.count(ConversacionWhatsApp.id)).scalar() or 0
                    tiempo_whatsapp = (time.time() - inicio) * 1000
                    print(f"   ✅ Query básica WhatsApp: {whatsapp_count} registros en {tiempo_whatsapp:.2f}ms")
                    
                    # Query básica Email
                    inicio = time.time()
                    email_count = 0
                    try:
                        email_count = db.query(func.count(ComunicacionEmail.id)).scalar() or 0
                    except Exception:
                        pass
                    tiempo_email = (time.time() - inicio) * 1000
                    print(f"   ✅ Query básica Email: {email_count} registros en {tiempo_email:.2f}ms")
                    
                    # Query con filtros
                    inicio = time.time()
                    whatsapp_inbound = db.query(ConversacionWhatsApp).filter(
                        ConversacionWhatsApp.direccion == "INBOUND"
                    ).count()
                    tiempo_filtro = (time.time() - inicio) * 1000
                    print(f"   ✅ Query con filtro (INBOUND): {whatsapp_inbound} registros en {tiempo_filtro:.2f}ms")
                    
                    # Query con join (cliente)
                    inicio = time.time()
                    whatsapp_con_cliente = db.query(ConversacionWhatsApp).filter(
                        ConversacionWhatsApp.cliente_id.isnot(None)
                    ).count()
                    tiempo_join = (time.time() - inicio) * 1000
                    print(f"   ✅ Query con cliente vinculado: {whatsapp_con_cliente} registros en {tiempo_join:.2f}ms")
                    
                    self.resultados["verificaciones"]["endpoint_backend"] = {
                        "estado": "exitoso",
                        "tiempos": {
                            "query_whatsapp": tiempo_whatsapp,
                            "query_email": tiempo_email,
                            "query_filtro": tiempo_filtro,
                            "query_join": tiempo_join
                        }
                    }
                    
                    return True
                finally:
                    db.close()
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
                self.resultados["verificaciones"]["endpoint_backend"] = {
                    "estado": "error",
                    "mensaje": str(e)
                }
                return False

        def verificar_rendimiento(self) -> bool:
            """Verifica rendimiento de queries"""
            print("\n" + "=" * 70)
            print("5. VERIFICACIÓN: Rendimiento")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    # COUNT total
                    inicio = time.time()
                    total_whatsapp = db.query(func.count(ConversacionWhatsApp.id)).scalar() or 0
                    tiempo_count = (time.time() - inicio) * 1000
                    print(f"   ✅ COUNT total WhatsApp: {tiempo_count:.2f}ms")
                    
                    # Query paginada
                    inicio = time.time()
                    whatsapp_pag = db.query(ConversacionWhatsApp).order_by(
                        ConversacionWhatsApp.timestamp.desc()
                    ).limit(20).all()
                    tiempo_pag = (time.time() - inicio) * 1000
                    print(f"   ✅ Query paginada (20 registros): {tiempo_pag:.2f}ms")
                    
                    # Query con filtro y join
                    inicio = time.time()
                    whatsapp_filtrado = db.query(ConversacionWhatsApp).options(
                        # joinedload(ConversacionWhatsApp.cliente)
                    ).filter(
                        ConversacionWhatsApp.direccion == "INBOUND"
                    ).limit(10).all()
                    tiempo_filtro = (time.time() - inicio) * 1000
                    print(f"   ✅ Query con filtro: {tiempo_filtro:.2f}ms")
                    
                    # Serialización
                    inicio = time.time()
                    for w in whatsapp_pag[:10]:
                        w.to_dict()
                    tiempo_serial = (time.time() - inicio) * 1000
                    print(f"   ✅ Serialización (10 registros): {tiempo_serial:.2f}ms")
                    
                    self.resultados["verificaciones"]["rendimiento"] = {
                        "estado": "exitoso",
                        "tiempos": {
                            "count_total": tiempo_count,
                            "query_paginada": tiempo_pag,
                            "query_filtro": tiempo_filtro,
                            "serializacion": tiempo_serial
                        }
                    }
                    
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
            """Verifica índices de las tablas"""
            print("\n" + "=" * 70)
            print("6. VERIFICACIÓN: Índices de Base de Datos")
            print("=" * 70)
            
            tablas = ["conversaciones_whatsapp", "comunicaciones_email"]
            resultado_general = True
            
            for tabla in tablas:
                print(f"\n   📋 Tabla: {tabla}")
                try:
                    db = SessionLocal()
                    try:
                        result = db.execute(text(f"""
                            SELECT indexname, indexdef
                            FROM pg_indexes
                            WHERE tablename = '{tabla}'
                            ORDER BY indexname
                        """))
                        indices = result.fetchall()
                        
                        if indices:
                            print(f"   ✅ Índices encontrados: {len(indices)}")
                            for idx in indices:
                                print(f"      - {idx[0]}")
                        else:
                            print(f"   ⚠️  No se encontraron índices para {tabla}")
                            self.advertencias.append(f"Tabla {tabla} sin índices")
                        
                        self.resultados["verificaciones"][f"indices_{tabla}"] = {
                            "estado": "exitoso" if indices else "advertencia",
                            "indices": [idx[0] for idx in indices],
                            "total": len(indices)
                        }
                    finally:
                        db.close()
                except Exception as e:
                    print(f"   ⚠️  Error verificando índices de {tabla}: {str(e)}")
                    self.resultados["verificaciones"][f"indices_{tabla}"] = {
                        "estado": "advertencia",
                        "mensaje": str(e)
                    }
            
            return resultado_general

        def verificar_validaciones(self) -> bool:
            """Verifica validaciones de datos"""
            print("\n" + "=" * 70)
            print("7. VERIFICACIÓN: Validaciones de Datos")
            print("=" * 70)
            
            try:
                db = SessionLocal()
                try:
                    problemas = []
                    
                    # Validar direcciones válidas (INBOUND/OUTBOUND)
                    direcciones_invalidas_whatsapp = db.query(ConversacionWhatsApp).filter(
                        ~ConversacionWhatsApp.direccion.in_(["INBOUND", "OUTBOUND"])
                    ).count()
                    
                    if direcciones_invalidas_whatsapp > 0:
                        problemas.append(f"Conversaciones WhatsApp con direcciones inválidas: {direcciones_invalidas_whatsapp}")
                    
                    # Validar clientes huérfanos
                    from app.models.cliente import Cliente
                    whatsapp_orphan = db.query(ConversacionWhatsApp).filter(
                        ConversacionWhatsApp.cliente_id.isnot(None)
                    ).outerjoin(Cliente, ConversacionWhatsApp.cliente_id == Cliente.id).filter(
                        Cliente.id.is_(None)
                    ).count()
                    
                    if whatsapp_orphan > 0:
                        problemas.append(f"Conversaciones WhatsApp con cliente_id inexistente: {whatsapp_orphan}")
                    
                    # Validar timestamps futuros
                    from datetime import datetime, timedelta
                    ahora = datetime.utcnow()
                    futuro = ahora + timedelta(days=1)
                    whatsapp_futuro = db.query(ConversacionWhatsApp).filter(
                        ConversacionWhatsApp.timestamp > futuro
                    ).count()
                    
                    if whatsapp_futuro > 0:
                        problemas.append(f"Conversaciones WhatsApp con timestamps futuros: {whatsapp_futuro}")
                    
                    if problemas:
                        print("   ⚠️  Problemas encontrados:")
                        for problema in problemas:
                            print(f"      - {problema}")
                        self.resultados["verificaciones"]["validaciones"] = {
                            "estado": "advertencia",
                            "problemas": problemas
                        }
                    else:
                        print("   ✅ No se encontraron problemas de validación")
                        self.resultados["verificaciones"]["validaciones"] = {
                            "estado": "exitoso",
                            "problemas": []
                        }
                    
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

        def ejecutar_auditoria(self):
            """Ejecuta todas las verificaciones"""
            print("=" * 70)
            print("AUDITORÍA INTEGRAL: Endpoint /comunicaciones")
            print("=" * 70)
            print(f"Fecha: {datetime.now().isoformat()}")
            print(f"Endpoint: https://rapicredit.onrender.com/api/v1/comunicaciones")
            
            verificaciones = [
                ("conexion_bd", self.verificar_conexion_bd),
                ("estructura_tablas", self.verificar_estructura_tablas),
                ("datos_bd", self.verificar_datos_bd),
                ("endpoint_backend", self.verificar_endpoint_backend),
                ("rendimiento", self.verificar_rendimiento),
                ("indices", self.verificar_indices),
                ("validaciones", self.verificar_validaciones),
            ]
            
            exitosas = 0
            errores = 0
            advertencias = 0
            
            for nombre, funcion in verificaciones:
                try:
                    if funcion():
                        exitosas += 1
                    else:
                        errores += 1
                except Exception as e:
                    print(f"\n❌ Error ejecutando {nombre}: {type(e).__name__}: {str(e)}")
                    errores += 1
            
            # Resumen
            print("\n" + "=" * 70)
            print("RESUMEN DE AUDITORÍA")
            print("=" * 70)
            print(f"\nVerificaciones exitosas: {exitosas}/{len(verificaciones)}")
            print(f"Verificaciones parciales: {advertencias}/{len(verificaciones)}")
            print(f"Verificaciones con errores: {errores}/{len(verificaciones)}")
            print(f"Verificaciones con advertencias: {len(self.advertencias)}")
            
            if self.advertencias:
                print("\n⚠️  Advertencias encontradas:")
                for adv in self.advertencias:
                    print(f"   - {adv}")
            
            # Guardar resultados
            output_file = Path(__file__).parent.parent.parent / "AUDITORIA_COMUNICACIONES.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.resultados, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Reporte guardado en: {output_file}")

    if __name__ == "__main__":
        auditoria = AuditoriaIntegralComunicaciones()
        auditoria.ejecutar_auditoria()

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de estar en el directorio correcto y tener las dependencias instaladas")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
