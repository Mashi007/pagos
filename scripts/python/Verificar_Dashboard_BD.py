"""
Script para verificar que el dashboard esté conectado correctamente a la base de datos
"""

import os
import sys
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from sqlalchemy import text
    from app.db.session import SessionLocal, engine, get_db, test_connection
    from app.models.dashboard_oficial import (
        DashboardCobranzasMensuales,
        DashboardFinanciamientoMensual,
        DashboardKPIsDiarios,
        DashboardMetricasAcumuladas,
        DashboardMorosidadMensual,
        DashboardMorosidadPorAnalista,
        DashboardPagosMensuales,
        DashboardPrestamosPorConcesionario,
    )
    from app.models.pago import Pago
    from app.models.prestamo import Prestamo
    from app.models.cliente import Cliente
    from app.models.amortizacion import Cuota
    import logging

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    def verificar_dashboard_bd():
        """Verifica que el dashboard esté conectado correctamente a la base de datos"""
        print("=" * 70)
        print("VERIFICACIÓN DE CONEXIÓN DEL DASHBOARD A BASE DE DATOS")
        print("=" * 70)

        resultados = {
            "conexion_basica": False,
            "tablas_dashboard": False,
            "modelos_accesibles": False,
            "queries_funcionando": False,
            "get_db_funcionando": False
        }

        # 1. Verificar conexión básica usando test_connection
        print("\n1. Verificando conexión básica a la base de datos...")
        try:
            if test_connection():
                print("   [OK] Conexion basica exitosa")
                resultados["conexion_basica"] = True
            else:
                print("   [ERROR] Conexion basica fallo")
                return resultados
        except Exception as e:
            print(f"   [ERROR] Error en conexion basica: {type(e).__name__}: {str(e)}")
            return resultados

        # 2. Verificar que get_db funciona correctamente
        print("\n2. Verificando función get_db()...")
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                # Ejecutar query de prueba
                result = db.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                if row and row[0] == 1:
                    print("   [OK] get_db() funciona correctamente")
                    resultados["get_db_funcionando"] = True
                else:
                    print("   [ADVERTENCIA] get_db() retorno resultado inesperado")
            finally:
                db.close()
                try:
                    next(db_gen)  # Consumir el generador completamente
                except StopIteration:
                    pass
        except Exception as e:
            print(f"   [ERROR] Error en get_db(): {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()

        # 3. Verificar existencia de tablas del dashboard
        print("\n3. Verificando tablas del dashboard...")
        tablas_dashboard = [
            'dashboard_cobranzas_mensuales',
            'dashboard_financiamiento_mensual',
            'dashboard_kpis_diarios',
            'dashboard_metricas_acumuladas',
            'dashboard_morosidad_mensual',
            'dashboard_morosidad_por_analista',
            'dashboard_pagos_mensuales',
            'dashboard_prestamos_por_concesionario'
        ]
        tablas_encontradas = []
        tablas_faltantes = []

        try:
            db = SessionLocal()
            try:
                # Obtener lista de tablas
                query_tablas = text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    AND table_name LIKE 'dashboard%'
                """)
                result = db.execute(query_tablas)
                tablas_existentes = [row[0].lower() for row in result.fetchall()]

                for tabla in tablas_dashboard:
                    if tabla in tablas_existentes:
                        tablas_encontradas.append(tabla)
                        print(f"   [OK] Tabla '{tabla}' existe")
                    else:
                        tablas_faltantes.append(tabla)
                        print(f"   [ADVERTENCIA] Tabla '{tabla}' NO existe (puede ser normal si usa vistas materializadas)")

                if len(tablas_encontradas) > 0:
                    resultados["tablas_dashboard"] = True
                    print(f"\n   📊 Total: {len(tablas_encontradas)} tablas encontradas, {len(tablas_faltantes)} faltantes")
                else:
                    print("   [ADVERTENCIA] No se encontraron tablas del dashboard (puede usar vistas o queries directas)")
            finally:
                db.close()
        except Exception as e:
            print(f"   [ADVERTENCIA] Error verificando tablas: {type(e).__name__}: {str(e)}")

        # 4. Verificar que los modelos del dashboard sean accesibles
        print("\n4. Verificando acceso a modelos del dashboard...")
        modelos_verificados = []
        try:
            db = SessionLocal()
            try:
                # Verificar DashboardCobranzasMensuales
                try:
                    count = db.query(DashboardCobranzasMensuales).count()
                    print(f"   [OK] DashboardCobranzasMensuales accesible - {count} registros")
                    modelos_verificados.append("DashboardCobranzasMensuales")
                except Exception as e:
                    print(f"   [ADVERTENCIA] DashboardCobranzasMensuales: {type(e).__name__}: {str(e)}")

                # Verificar DashboardKPIsDiarios
                try:
                    count = db.query(DashboardKPIsDiarios).count()
                    print(f"   [OK] DashboardKPIsDiarios accesible - {count} registros")
                    modelos_verificados.append("DashboardKPIsDiarios")
                except Exception as e:
                    print(f"   [ADVERTENCIA] DashboardKPIsDiarios: {type(e).__name__}: {str(e)}")

                # Verificar DashboardMorosidadMensual
                try:
                    count = db.query(DashboardMorosidadMensual).count()
                    print(f"   [OK] DashboardMorosidadMensual accesible - {count} registros")
                    modelos_verificados.append("DashboardMorosidadMensual")
                except Exception as e:
                    print(f"   [ADVERTENCIA] DashboardMorosidadMensual: {type(e).__name__}: {str(e)}")

                if len(modelos_verificados) > 0:
                    resultados["modelos_accesibles"] = True
            finally:
                db.close()
        except Exception as e:
            print(f"   [ADVERTENCIA] Error verificando modelos: {type(e).__name__}: {str(e)}")

        # 5. Verificar tablas base necesarias para el dashboard
        print("\n5. Verificando tablas base necesarias para el dashboard...")
        tablas_base = ['pagos', 'prestamos', 'cuotas', 'clientes']
        tablas_base_encontradas = []
        try:
            db = SessionLocal()
            try:
                query_tablas = text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """)
                result = db.execute(query_tablas)
                tablas_existentes = [row[0].lower() for row in result.fetchall()]

                for tabla in tablas_base:
                    if tabla in tablas_existentes:
                        tablas_base_encontradas.append(tabla)
                        # Contar registros
                        try:
                            count_query = text(f"SELECT COUNT(*) FROM {tabla}")
                            count_result = db.execute(count_query)
                            count = count_result.scalar()
                            print(f"   [OK] Tabla '{tabla}' existe - {count} registros")
                        except Exception as e:
                            print(f"   [OK] Tabla '{tabla}' existe (error contando: {str(e)})")
                    else:
                        print(f"   [ERROR] Tabla '{tabla}' NO existe - CRITICO para el dashboard")
            finally:
                db.close()
        except Exception as e:
            print(f"   [ADVERTENCIA] Error verificando tablas base: {type(e).__name__}: {str(e)}")

        # 6. Verificar queries típicas del dashboard
        print("\n6. Verificando queries típicas del dashboard...")
        try:
            db = SessionLocal()
            try:
                # Query 1: Contar pagos del mes actual
                try:
                    query_pagos = text("""
                        SELECT COUNT(*) 
                        FROM pagos 
                        WHERE DATE_TRUNC('month', fecha_pago) = DATE_TRUNC('month', CURRENT_DATE)
                    """)
                    result = db.execute(query_pagos)
                    count_pagos = result.scalar()
                    print(f"   [OK] Query de pagos mensuales funciona - {count_pagos} pagos este mes")
                    resultados["queries_funcionando"] = True
                except Exception as e:
                    print(f"   [ADVERTENCIA] Query de pagos mensuales: {type(e).__name__}: {str(e)}")

                # Query 2: Contar préstamos activos
                try:
                    query_prestamos = text("""
                        SELECT COUNT(*) 
                        FROM prestamos 
                        WHERE estado IN ('ACTIVO', 'VIGENTE')
                    """)
                    result = db.execute(query_prestamos)
                    count_prestamos = result.scalar()
                    print(f"   [OK] Query de prestamos activos funciona - {count_prestamos} prestamos activos")
                except Exception as e:
                    print(f"   [ADVERTENCIA] Query de prestamos activos: {type(e).__name__}: {str(e)}")

                # Query 3: Verificar cuotas
                try:
                    query_cuotas = text("""
                        SELECT COUNT(*) 
                        FROM cuotas 
                        WHERE estado = 'PENDIENTE'
                    """)
                    result = db.execute(query_cuotas)
                    count_cuotas = result.scalar()
                    print(f"   [OK] Query de cuotas pendientes funciona - {count_cuotas} cuotas pendientes")
                except Exception as e:
                    print(f"   [ADVERTENCIA] Query de cuotas pendientes: {type(e).__name__}: {str(e)}")

            finally:
                db.close()
        except Exception as e:
            print(f"   [ADVERTENCIA] Error verificando queries: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()

        # 7. Verificar que el engine esté configurado correctamente
        print("\n7. Verificando configuración del engine...")
        try:
            if engine:
                print(f"   [OK] Engine configurado")
                print(f"   [INFO] Pool size: {engine.pool.size()}")
                print(f"   [INFO] Pool checked out: {engine.pool.checkedout()}")
                print(f"   [INFO] Pool overflow: {engine.pool.overflow()}")
            else:
                print("   [ERROR] Engine NO esta configurado")
        except Exception as e:
            print(f"   [ADVERTENCIA] Error verificando engine: {type(e).__name__}: {str(e)}")

        # Resumen final
        print("\n" + "=" * 70)
        print("RESUMEN DE VERIFICACIÓN")
        print("=" * 70)
        
        total_verificaciones = len(resultados)
        verificaciones_exitosas = sum(1 for v in resultados.values() if v)
        
        print(f"\n[OK] Verificaciones exitosas: {verificaciones_exitosas}/{total_verificaciones}")
        print("\nDetalle:")
        for verificacion, resultado in resultados.items():
            estado = "[OK]" if resultado else "[ERROR]"
            print(f"   {estado} {verificacion}: {resultado}")

        if verificaciones_exitosas == total_verificaciones:
            print("\n[EXITO] Todas las verificaciones pasaron! El dashboard esta correctamente conectado.")
        elif resultados["conexion_basica"] and resultados["get_db_funcionando"]:
            print("\n[ADVERTENCIA] Conexion basica OK, pero algunas verificaciones fallaron.")
            print("   El dashboard deberia funcionar, pero puede tener limitaciones.")
        else:
            print("\n[ERROR] Hay problemas criticos con la conexion a la base de datos.")
            print("   El dashboard NO funcionara correctamente hasta resolver estos problemas.")

        return resultados

    if __name__ == "__main__":
        resultados = verificar_dashboard_bd()
        # Salir con código de error si hay problemas críticos
        if not resultados.get("conexion_basica", False) or not resultados.get("get_db_funcionando", False):
            sys.exit(1)
        sys.exit(0)

except ImportError as e:
    print(f"[ERROR] Error importando modulos: {e}")
    print("Asegurate de ejecutar este script desde la raiz del proyecto")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error inesperado: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
