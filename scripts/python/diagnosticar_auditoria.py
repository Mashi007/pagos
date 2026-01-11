"""
Script para diagnosticar problemas con el endpoint de auditoría
Verifica tablas, datos y el endpoint directamente
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.db.session import SessionLocal, test_connection
    from app.models.auditoria import Auditoria
    from app.models.pago_auditoria import PagoAuditoria
    from app.models.prestamo_auditoria import PrestamoAuditoria
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

    def diagnosticar_auditoria():
        """Diagnostica problemas con el endpoint de auditoría"""
        print("=" * 80)
        print("🔍 DIAGNÓSTICO DEL ENDPOINT DE AUDITORÍA")
        print("=" * 80)

        resultados = {
            "conexion_bd": False,
            "tabla_auditoria_existe": False,
            "tabla_prestamos_auditoria_existe": False,
            "tabla_pagos_auditoria_existe": False,
            "datos_en_auditoria": False,
            "datos_en_prestamos_auditoria": False,
            "datos_en_pagos_auditoria": False,
            "modelos_funcionan": False,
        }

        # 1. Verificar conexión a base de datos
        print("\n1️⃣ Verificando conexión a base de datos...")
        try:
            if test_connection():
                print("   ✅ Conexión a base de datos exitosa")
                resultados["conexion_bd"] = True
            else:
                print("   ❌ Error en conexión a base de datos")
                return resultados
        except Exception as e:
            print(f"   ❌ Error verificando conexión: {type(e).__name__}: {str(e)}")
            return resultados

        # 2. Verificar existencia de tablas de auditoría
        print("\n2️⃣ Verificando existencia de tablas de auditoría...")
        try:
            db = SessionLocal()
            try:
                inspector = inspect(db.bind)
                tablas = inspector.get_table_names()
                
                tabla_auditoria_existe = "auditoria" in tablas
                tabla_prestamos_auditoria_existe = "prestamos_auditoria" in tablas
                tabla_pagos_auditoria_existe = "pagos_auditoria" in tablas
                
                print(f"   📋 Tablas encontradas en BD: {len(tablas)}")
                print(f"   {'✅' if tabla_auditoria_existe else '❌'} Tabla 'auditoria': {'existe' if tabla_auditoria_existe else 'NO existe'}")
                print(f"   {'✅' if tabla_prestamos_auditoria_existe else '❌'} Tabla 'prestamos_auditoria': {'existe' if tabla_prestamos_auditoria_existe else 'NO existe'}")
                print(f"   {'✅' if tabla_pagos_auditoria_existe else '❌'} Tabla 'pagos_auditoria': {'existe' if tabla_pagos_auditoria_existe else 'NO existe'}")
                
                resultados["tabla_auditoria_existe"] = tabla_auditoria_existe
                resultados["tabla_prestamos_auditoria_existe"] = tabla_prestamos_auditoria_existe
                resultados["tabla_pagos_auditoria_existe"] = tabla_pagos_auditoria_existe
                
                if not tabla_auditoria_existe and not tabla_prestamos_auditoria_existe and not tabla_pagos_auditoria_existe:
                    print("\n   ⚠️  PROBLEMA DETECTADO: Ninguna tabla de auditoría existe")
                    print("   💡 Solución: Ejecutar migraciones de Alembic")
                    print("   💡 Comando: alembic upgrade head")
                    return resultados
                    
            except Exception as e:
                print(f"   ❌ Error verificando tablas: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                db.close()
        except Exception as e:
            print(f"   ❌ Error creando sesión: {type(e).__name__}: {str(e)}")
            return resultados

        # 3. Verificar datos en las tablas
        print("\n3️⃣ Verificando datos en las tablas de auditoría...")
        try:
            db = SessionLocal()
            try:
                # Verificar tabla auditoria
                if tabla_auditoria_existe:
                    try:
                        count_auditoria = db.execute(text("SELECT COUNT(*) FROM auditoria")).scalar()
                        print(f"   📊 Tabla 'auditoria': {count_auditoria} registros")
                        resultados["datos_en_auditoria"] = count_auditoria > 0
                        
                        if count_auditoria > 0:
                            # Mostrar algunos registros recientes
                            registros_recientes = db.execute(
                                text("SELECT id, accion, entidad, fecha FROM auditoria ORDER BY fecha DESC LIMIT 5")
                            ).fetchall()
                            print(f"   📝 Últimos 5 registros:")
                            for reg in registros_recientes:
                                print(f"      - ID: {reg[0]}, Acción: {reg[1]}, Módulo: {reg[2]}, Fecha: {reg[3]}")
                    except Exception as e:
                        print(f"   ⚠️  Error consultando tabla 'auditoria': {type(e).__name__}: {str(e)}")
                
                # Verificar tabla prestamos_auditoria
                if tabla_prestamos_auditoria_existe:
                    try:
                        count_prestamos = db.execute(text("SELECT COUNT(*) FROM prestamos_auditoria")).scalar()
                        print(f"   📊 Tabla 'prestamos_auditoria': {count_prestamos} registros")
                        resultados["datos_en_prestamos_auditoria"] = count_prestamos > 0
                        
                        if count_prestamos > 0:
                            registros_recientes = db.execute(
                                text("SELECT id, accion, campo_modificado, fecha_cambio FROM prestamos_auditoria ORDER BY fecha_cambio DESC LIMIT 5")
                            ).fetchall()
                            print(f"   📝 Últimos 5 registros:")
                            for reg in registros_recientes:
                                print(f"      - ID: {reg[0]}, Acción: {reg[1]}, Campo: {reg[2]}, Fecha: {reg[3]}")
                    except Exception as e:
                        print(f"   ⚠️  Error consultando tabla 'prestamos_auditoria': {type(e).__name__}: {str(e)}")
                
                # Verificar tabla pagos_auditoria
                if tabla_pagos_auditoria_existe:
                    try:
                        count_pagos = db.execute(text("SELECT COUNT(*) FROM pagos_auditoria")).scalar()
                        print(f"   📊 Tabla 'pagos_auditoria': {count_pagos} registros")
                        resultados["datos_en_pagos_auditoria"] = count_pagos > 0
                        
                        if count_pagos > 0:
                            registros_recientes = db.execute(
                                text("SELECT id, accion, campo_modificado, fecha_cambio FROM pagos_auditoria ORDER BY fecha_cambio DESC LIMIT 5")
                            ).fetchall()
                            print(f"   📝 Últimos 5 registros:")
                            for reg in registros_recientes:
                                print(f"      - ID: {reg[0]}, Acción: {reg[1]}, Campo: {reg[2]}, Fecha: {reg[3]}")
                    except Exception as e:
                        print(f"   ⚠️  Error consultando tabla 'pagos_auditoria': {type(e).__name__}: {str(e)}")
                
                total_registros = (
                    (count_auditoria if tabla_auditoria_existe else 0) +
                    (count_prestamos if tabla_prestamos_auditoria_existe else 0) +
                    (count_pagos if tabla_pagos_auditoria_existe else 0)
                )
                
                if total_registros == 0:
                    print("\n   ⚠️  PROBLEMA DETECTADO: No hay registros de auditoría en ninguna tabla")
                    print("   💡 Esto es normal si:")
                    print("      - El sistema es nuevo y no se han realizado acciones")
                    print("      - La auditoría no está activada")
                    print("   💡 Para generar datos de prueba, realiza algunas acciones en el sistema")
                    
            except Exception as e:
                print(f"   ❌ Error verificando datos: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                db.close()
        except Exception as e:
            print(f"   ❌ Error creando sesión: {type(e).__name__}: {str(e)}")

        # 4. Verificar que los modelos funcionan
        print("\n4️⃣ Verificando modelos de auditoría...")
        try:
            db = SessionLocal()
            try:
                modelos_ok = True
                
                if tabla_auditoria_existe:
                    try:
                        count = db.query(Auditoria).count()
                        print(f"   ✅ Modelo Auditoria funciona - Total: {count}")
                    except Exception as e:
                        print(f"   ❌ Error con modelo Auditoria: {type(e).__name__}: {str(e)}")
                        modelos_ok = False
                
                if tabla_prestamos_auditoria_existe:
                    try:
                        count = db.query(PrestamoAuditoria).count()
                        print(f"   ✅ Modelo PrestamoAuditoria funciona - Total: {count}")
                    except Exception as e:
                        print(f"   ❌ Error con modelo PrestamoAuditoria: {type(e).__name__}: {str(e)}")
                        modelos_ok = False
                
                if tabla_pagos_auditoria_existe:
                    try:
                        count = db.query(PagoAuditoria).count()
                        print(f"   ✅ Modelo PagoAuditoria funciona - Total: {count}")
                    except Exception as e:
                        print(f"   ❌ Error con modelo PagoAuditoria: {type(e).__name__}: {str(e)}")
                        modelos_ok = False
                
                resultados["modelos_funcionan"] = modelos_ok
                
            except Exception as e:
                print(f"   ❌ Error verificando modelos: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                db.close()
        except Exception as e:
            print(f"   ❌ Error creando sesión: {type(e).__name__}: {str(e)}")

        # Resumen final
        print("\n" + "=" * 80)
        print("📋 RESUMEN DEL DIAGNÓSTICO")
        print("=" * 80)
        
        total_verificaciones = len(resultados)
        verificaciones_exitosas = sum(1 for v in resultados.values() if v)
        
        print(f"\nVerificaciones exitosas: {verificaciones_exitosas}/{total_verificaciones}")
        for nombre, resultado in resultados.items():
            estado = "✅" if resultado else "❌"
            print(f"  {estado} {nombre.replace('_', ' ').title()}")
        
        print("\n" + "=" * 80)
        print("💡 RECOMENDACIONES")
        print("=" * 80)
        
        if not resultados["conexion_bd"]:
            print("❌ No se puede conectar a la base de datos")
            print("   Verifica la configuración de DATABASE_URL")
        elif not any([resultados["tabla_auditoria_existe"], 
                     resultados["tabla_prestamos_auditoria_existe"], 
                     resultados["tabla_pagos_auditoria_existe"]]):
            print("⚠️  Las tablas de auditoría no existen")
            print("   Ejecuta: alembic upgrade head")
        elif not any([resultados["datos_en_auditoria"], 
                     resultados["datos_en_prestamos_auditoria"], 
                     resultados["datos_en_pagos_auditoria"]]):
            print("⚠️  Las tablas existen pero no hay datos")
            print("   Esto es normal si el sistema es nuevo")
            print("   Realiza algunas acciones en el sistema para generar datos de auditoría")
        else:
            print("✅ Todo parece estar funcionando correctamente")
            print("   Si aún no aparecen datos en el frontend, verifica:")
            print("   - La autenticación del usuario")
            print("   - Los logs del servidor para errores")
            print("   - La consola del navegador para errores de red")
        
        return resultados

    if __name__ == "__main__":
        resultados = diagnosticar_auditoria()
        # Salir con código de error si hay problemas críticos
        problemas_criticos = (
            not resultados.get("conexion_bd", False) or
            (not resultados.get("tabla_auditoria_existe", False) and
             not resultados.get("tabla_prestamos_auditoria_existe", False) and
             not resultados.get("tabla_pagos_auditoria_existe", False))
        )
        sys.exit(0 if not problemas_criticos else 1)

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de ejecutar este script desde la raíz del proyecto")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
