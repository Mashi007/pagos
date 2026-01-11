"""
Script para verificar el correcto funcionamiento del endpoint /clientes
y su conexión a la base de datos
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from sqlalchemy import create_engine, text, func
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.db.session import SessionLocal, engine, get_db, test_connection
    from app.models.cliente import Cliente
    import logging

    # Configurar logging y encoding para Windows
    import io
    import sys
    # Configurar stdout para UTF-8 en Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    def verificar_endpoint_clientes():
        """Verifica el correcto funcionamiento del endpoint /clientes"""
        print("=" * 70)
        print("VERIFICACIÓN: ENDPOINT /clientes Y CONEXIÓN A BASE DE DATOS")
        print("=" * 70)

        resultados = {
            "conexion_bd": False,
            "tabla_existe": False,
            "modelo_funciona": False,
            "consultas_basicas": False,
            "datos_accesibles": False,
        }

        # 1. Verificar conexión a base de datos
        print("\n1. Verificando conexión a base de datos...")
        try:
            # Usar la función de test del módulo session
            if test_connection():
                print("   ✅ Conexión a base de datos exitosa")
                resultados["conexion_bd"] = True
            else:
                print("   ❌ Error en conexión a base de datos")
                return resultados
        except Exception as e:
            print(f"   ❌ Error verificando conexión: {type(e).__name__}: {str(e)}")
            return resultados

        # 2. Verificar que la tabla clientes existe
        print("\n2. Verificando existencia de tabla 'clientes'...")
        try:
            db = SessionLocal()
            try:
                # Verificar que la tabla existe ejecutando una query simple
                result = db.execute(text("SELECT COUNT(*) FROM clientes"))
                count = result.scalar()
                print(f"   ✅ Tabla 'clientes' existe - Total registros: {count}")
                resultados["tabla_existe"] = True
            except Exception as e:
                print(f"   ❌ Error accediendo tabla 'clientes': {type(e).__name__}: {str(e)}")
                # Intentar verificar si la tabla existe de otra forma
                try:
                    if settings.DATABASE_URL.startswith("postgresql"):
                        result = db.execute(text("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'public' 
                                AND table_name = 'clientes'
                            )
                        """))
                        exists = result.scalar()
                        if exists:
                            print("   ⚠️  Tabla existe pero hay problemas de acceso")
                            resultados["tabla_existe"] = True
                        else:
                            print("   ❌ Tabla 'clientes' NO existe en la base de datos")
                    else:
                        print("   ⚠️  No se pudo verificar existencia de tabla (SQLite)")
                except Exception as e2:
                    print(f"   ❌ Error verificando existencia: {type(e2).__name__}: {str(e2)}")
            finally:
                db.close()
        except Exception as e:
            print(f"   ❌ Error creando sesión: {type(e).__name__}: {str(e)}")
            return resultados

        # 3. Verificar que el modelo Cliente funciona correctamente
        print("\n3. Verificando modelo Cliente...")
        try:
            db = SessionLocal()
            try:
                # Intentar hacer una query usando el modelo ORM
                total_clientes = db.query(func.count(Cliente.id)).scalar()
                print(f"   ✅ Modelo Cliente funciona correctamente - Total: {total_clientes}")
                resultados["modelo_funciona"] = True
            except Exception as e:
                print(f"   ❌ Error usando modelo Cliente: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                db.close()
        except Exception as e:
            print(f"   ❌ Error creando sesión para modelo: {type(e).__name__}: {str(e)}")

        # 4. Verificar consultas básicas (similares a las del endpoint)
        print("\n4. Verificando consultas básicas del endpoint...")
        try:
            db = SessionLocal()
            try:
                # Query base como en el endpoint
                query = db.query(Cliente)
                
                # Contar total
                total = query.count()
                print(f"   ✅ Query COUNT funciona - Total: {total}")
                
                # Obtener algunos registros con paginación
                clientes = query.order_by(Cliente.fecha_registro.desc()).limit(5).all()
                print(f"   ✅ Query con paginación funciona - Registros obtenidos: {len(clientes)}")
                
                # Verificar filtros
                if total > 0:
                    # Probar filtro por estado
                    activos = query.filter(Cliente.estado == "ACTIVO").count()
                    print(f"   ✅ Filtro por estado funciona - Activos: {activos}")
                    
                    # Probar búsqueda por cédula
                    primer_cliente = clientes[0] if clientes else None
                    if primer_cliente and primer_cliente.cedula:
                        busqueda = query.filter(Cliente.cedula.ilike(f"%{primer_cliente.cedula[:5]}%")).count()
                        print(f"   ✅ Búsqueda por cédula funciona - Resultados: {busqueda}")
                
                resultados["consultas_basicas"] = True
            except Exception as e:
                print(f"   ❌ Error en consultas básicas: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                db.close()
        except Exception as e:
            print(f"   ❌ Error creando sesión para consultas: {type(e).__name__}: {str(e)}")

        # 5. Verificar acceso a datos (serialización)
        print("\n5. Verificando serialización de datos...")
        try:
            db = SessionLocal()
            try:
                # Obtener un cliente y verificar que se puede serializar
                cliente = db.query(Cliente).first()
                if cliente:
                    # Verificar campos principales
                    campos_requeridos = ['id', 'cedula', 'nombres', 'telefono', 'email', 
                                       'direccion', 'estado', 'fecha_registro']
                    campos_presentes = []
                    campos_faltantes = []
                    
                    for campo in campos_requeridos:
                        if hasattr(cliente, campo):
                            valor = getattr(cliente, campo)
                            campos_presentes.append(campo)
                            print(f"   ✅ Campo '{campo}': {type(valor).__name__} = {str(valor)[:50]}")
                        else:
                            campos_faltantes.append(campo)
                    
                    if campos_faltantes:
                        print(f"   ⚠️  Campos faltantes: {campos_faltantes}")
                    else:
                        print(f"   ✅ Todos los campos requeridos están presentes")
                        resultados["datos_accesibles"] = True
                else:
                    print("   ⚠️  No hay clientes en la base de datos para verificar serialización")
                    resultados["datos_accesibles"] = True  # No es un error si no hay datos
            except Exception as e:
                print(f"   ❌ Error verificando serialización: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                db.close()
        except Exception as e:
            print(f"   ❌ Error creando sesión para serialización: {type(e).__name__}: {str(e)}")

        # 6. Verificar estructura de la tabla
        print("\n6. Verificando estructura de la tabla 'clientes'...")
        try:
            db = SessionLocal()
            try:
                if settings.DATABASE_URL.startswith("postgresql"):
                    result = db.execute(text("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_name = 'clientes'
                        ORDER BY ordinal_position
                    """))
                    columnas = result.fetchall()
                    print(f"   ✅ Columnas encontradas: {len(columnas)}")
                    for col in columnas[:10]:  # Mostrar primeras 10
                        print(f"      - {col[0]} ({col[1]}, nullable: {col[2]})")
                    if len(columnas) > 10:
                        print(f"      ... y {len(columnas) - 10} más")
                else:
                    print("   ⚠️  Verificación de estructura no disponible para SQLite")
            except Exception as e:
                print(f"   ⚠️  Error verificando estructura: {type(e).__name__}: {str(e)}")
            finally:
                db.close()
        except Exception as e:
            print(f"   ⚠️  Error creando sesión para estructura: {type(e).__name__}: {str(e)}")

        # Resumen final
        print("\n" + "=" * 70)
        print("RESUMEN DE VERIFICACIÓN")
        print("=" * 70)
        
        total_verificaciones = len(resultados)
        verificaciones_exitosas = sum(1 for v in resultados.values() if v)
        
        print(f"\nVerificaciones exitosas: {verificaciones_exitosas}/{total_verificaciones}")
        for nombre, resultado in resultados.items():
            estado = "✅" if resultado else "❌"
            print(f"  {estado} {nombre.replace('_', ' ').title()}")
        
        if verificaciones_exitosas == total_verificaciones:
            print("\n✅ TODAS LAS VERIFICACIONES PASARON CORRECTAMENTE")
            print("   El endpoint /clientes debería funcionar correctamente")
        else:
            print(f"\n⚠️  {total_verificaciones - verificaciones_exitosas} VERIFICACIONES FALLARON")
            print("   Revisa los errores anteriores para identificar el problema")
        
        return resultados

    if __name__ == "__main__":
        resultados = verificar_endpoint_clientes()
        # Salir con código de error si alguna verificación falló
        todas_exitosas = all(resultados.values())
        sys.exit(0 if todas_exitosas else 1)

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
