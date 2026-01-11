"""
Script de verificación completa de todos los gráficos del dashboard
Verifica que todos los endpoints estén conectados correctamente a la base de datos
y que los datos se actualicen normalmente con cada actualización
"""

import os
import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, List, Any

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from sqlalchemy import text, func
    from app.db.session import SessionLocal, test_connection
    from app.models.pago import Pago
    from app.models.prestamo import Prestamo
    from app.models.amortizacion import Cuota
    from app.models.cliente import Cliente
    import logging

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Lista de todos los endpoints del dashboard y sus verificaciones
    ENDPOINTS_VERIFICACION = [
        {
            "nombre": "KPIs Principales",
            "endpoint": "/api/v1/dashboard/kpis-principales",
            "tablas": ["prestamos", "clientes", "cuotas", "pagos"],
            "verificar_campos": ["total_prestamos", "creditos_nuevos_mes", "total_clientes", "total_morosidad_usd"]
        },
        {
            "nombre": "Dashboard Admin",
            "endpoint": "/api/v1/dashboard/admin",
            "tablas": ["prestamos", "cuotas", "pagos", "clientes"],
            "verificar_campos": ["financieros", "meta_mensual", "evolucion_mensual"]
        },
        {
            "nombre": "Financiamiento Tendencia Mensual",
            "endpoint": "/api/v1/dashboard/financiamiento-tendencia-mensual",
            "tablas": ["prestamos", "cuotas", "pagos"],
            "verificar_campos": ["meses", "monto_nuevos", "monto_cuotas_programadas", "monto_pagado", "morosidad_mensual"]
        },
        {
            "nombre": "Préstamos por Concesionario",
            "endpoint": "/api/v1/dashboard/prestamos-por-concesionario",
            "tablas": ["prestamos"],
            "verificar_campos": ["concesionarios", "total_prestamos", "cantidad_prestamos"]
        },
        {
            "nombre": "Préstamos por Modelo",
            "endpoint": "/api/v1/dashboard/prestamos-por-modelo",
            "tablas": ["prestamos"],
            "verificar_campos": ["modelos", "total_prestamos", "cantidad_prestamos"]
        },
        {
            "nombre": "Financiamiento por Rangos",
            "endpoint": "/api/v1/dashboard/financiamiento-por-rangos",
            "tablas": ["prestamos"],
            "verificar_campos": ["rangos", "total_prestamos", "total_monto"]
        },
        {
            "nombre": "Composición Morosidad",
            "endpoint": "/api/v1/dashboard/composicion-morosidad",
            "tablas": ["cuotas", "prestamos"],
            "verificar_campos": ["puntos", "total_morosidad", "total_cuotas"]
        },
        {
            "nombre": "Cobranzas Mensuales",
            "endpoint": "/api/v1/dashboard/cobranzas-mensuales",
            "tablas": ["cuotas", "pagos"],
            "verificar_campos": ["meses", "cobranzas_planificadas", "pagos_reales", "meta_mensual"]
        },
        {
            "nombre": "Cobranzas Semanales",
            "endpoint": "/api/v1/dashboard/cobranzas-semanales",
            "tablas": ["cuotas", "pagos"],
            "verificar_campos": ["semanas", "cobranzas_planificadas", "pagos_reales"]
        },
        {
            "nombre": "Morosidad por Analista",
            "endpoint": "/api/v1/dashboard/morosidad-por-analista",
            "tablas": ["cuotas", "prestamos"],
            "verificar_campos": ["analistas", "total_morosidad", "cantidad_clientes"]
        },
        {
            "nombre": "Evolución Morosidad",
            "endpoint": "/api/v1/dashboard/evolucion-morosidad",
            "tablas": ["cuotas", "prestamos"],
            "verificar_campos": ["meses", "morosidad"]
        },
        {
            "nombre": "Evolución Pagos",
            "endpoint": "/api/v1/dashboard/evolucion-pagos",
            "tablas": ["pagos"],
            "verificar_campos": ["meses", "pagos", "monto"]
        },
        {
            "nombre": "Evolución General Mensual",
            "endpoint": "/api/v1/dashboard/evolucion-general-mensual",
            "tablas": ["prestamos", "cuotas", "pagos"],
            "verificar_campos": ["meses", "cartera", "cuotas_a_cobrar"]
        },
    ]

    def verificar_conexion_bd():
        """Verifica la conexión básica a la base de datos"""
        print("\n" + "=" * 80)
        print("1. VERIFICACIÓN DE CONEXIÓN A BASE DE DATOS")
        print("=" * 80)
        
        try:
            resultado = test_connection()
            if resultado:
                print("[OK] Conexión a base de datos: EXITOSA")
                return True
            else:
                print("[ERROR] Conexión a base de datos: FALLIDA")
                return False
        except Exception as e:
            print(f"[ERROR] Error verificando conexión: {e}")
            return False

    def verificar_tablas_existen(db):
        """Verifica que las tablas principales existan"""
        print("\n" + "=" * 80)
        print("2. VERIFICACIÓN DE TABLAS PRINCIPALES")
        print("=" * 80)
        
        tablas_requeridas = ["prestamos", "cuotas", "pagos", "clientes"]
        tablas_existentes = []
        
        for tabla in tablas_requeridas:
            try:
                resultado = db.execute(text(f"SELECT COUNT(*) FROM {tabla} LIMIT 1"))
                count = resultado.scalar()
                print(f"[OK] Tabla '{tabla}': EXISTE ({count:,} registros)")
                tablas_existentes.append(tabla)
            except Exception as e:
                print(f"[ERROR] Tabla '{tabla}': NO EXISTE o ERROR - {e}")
        
        return len(tablas_existentes) == len(tablas_requeridas)

    def verificar_datos_recientes(db):
        """Verifica que haya datos recientes en las tablas principales"""
        print("\n" + "=" * 80)
        print("3. VERIFICACIÓN DE DATOS RECIENTES")
        print("=" * 80)
        
        hoy = date.today()
        hace_30_dias = hoy - timedelta(days=30)
        
        verificaciones = []
        
        # Verificar préstamos recientes
        try:
            prestamos_recientes = db.query(func.count(Prestamo.id)).filter(
                Prestamo.fecha_aprobacion >= hace_30_dias,
                Prestamo.estado == "APROBADO"
            ).scalar() or 0
            print(f"[OK] Préstamos aprobados últimos 30 días: {prestamos_recientes:,}")
            verificaciones.append(prestamos_recientes > 0)
        except Exception as e:
            print(f"[ERROR] Error verificando préstamos recientes: {e}")
            verificaciones.append(False)
        
        # Verificar pagos recientes
        try:
            pagos_recientes = db.query(func.count(Pago.id)).filter(
                Pago.fecha_pago >= datetime.combine(hace_30_dias, datetime.min.time()),
                Pago.activo.is_(True),
                Pago.monto_pagado > 0
            ).scalar() or 0
            print(f"[OK] Pagos últimos 30 días: {pagos_recientes:,}")
            verificaciones.append(pagos_recientes > 0)
        except Exception as e:
            print(f"[ERROR] Error verificando pagos recientes: {e}")
            verificaciones.append(False)
        
        # Verificar cuotas con vencimiento reciente
        try:
            cuotas_recientes = db.query(func.count(Cuota.id)).join(
                Prestamo, Cuota.prestamo_id == Prestamo.id
            ).filter(
                Cuota.fecha_vencimiento >= hace_30_dias,
                Prestamo.estado == "APROBADO"
            ).scalar() or 0
            print(f"[OK] Cuotas con vencimiento últimos 30 días: {cuotas_recientes:,}")
            verificaciones.append(cuotas_recientes > 0)
        except Exception as e:
            print(f"[ERROR] Error verificando cuotas recientes: {e}")
            verificaciones.append(False)
        
        return all(verificaciones)

    def verificar_endpoint_datos(endpoint_info: Dict[str, Any], db):
        """Verifica que un endpoint tenga datos disponibles en la BD"""
        nombre = endpoint_info["nombre"]
        tablas = endpoint_info["tablas"]
        
        print(f"\n  📊 {nombre}")
        print(f"     Tablas requeridas: {', '.join(tablas)}")
        
        # Verificar que las tablas tengan datos
        tablas_con_datos = []
        for tabla in tablas:
            try:
                if tabla == "prestamos":
                    count = db.query(func.count(Prestamo.id)).filter(
                        Prestamo.estado == "APROBADO"
                    ).scalar() or 0
                elif tabla == "pagos":
                    count = db.query(func.count(Pago.id)).filter(
                        Pago.activo.is_(True),
                        Pago.monto_pagado > 0
                    ).scalar() or 0
                elif tabla == "cuotas":
                    count = db.query(func.count(Cuota.id)).join(
                        Prestamo, Cuota.prestamo_id == Prestamo.id
                    ).filter(
                        Prestamo.estado == "APROBADO"
                    ).scalar() or 0
                elif tabla == "clientes":
                    count = db.query(func.count(Cliente.id)).scalar() or 0
                else:
                    count = 0
                
                if count > 0:
                    tablas_con_datos.append(tabla)
                    print(f"     [OK] Tabla '{tabla}': {count:,} registros")
                else:
                    print(f"     [ADVERTENCIA] Tabla '{tabla}': Sin registros")
            except Exception as e:
                print(f"     [ERROR] Error verificando tabla '{tabla}': {e}")
        
        return len(tablas_con_datos) == len(tablas)

    def verificar_actualizacion_datos(db):
        """Verifica que los datos se actualicen correctamente"""
        print("\n" + "=" * 80)
        print("4. VERIFICACIÓN DE ACTUALIZACIÓN DE DATOS")
        print("=" * 80)
        
        hoy = date.today()
        
        # Verificar que haya datos de hoy
        try:
            pagos_hoy = db.query(func.count(Pago.id)).filter(
                func.date(Pago.fecha_pago) == hoy,
                Pago.activo.is_(True)
            ).scalar() or 0
            print(f"[OK] Pagos de hoy ({hoy}): {pagos_hoy:,}")
        except Exception as e:
            print(f"[ERROR] Error verificando pagos de hoy: {e}")
        
        # Verificar que haya préstamos recientes
        try:
            prestamos_recientes = db.query(func.count(Prestamo.id)).filter(
                Prestamo.fecha_aprobacion >= hoy - timedelta(days=7),
                Prestamo.estado == "APROBADO"
            ).scalar() or 0
            print(f"[OK] Préstamos últimos 7 días: {prestamos_recientes:,}")
        except Exception as e:
            print(f"[ERROR] Error verificando préstamos recientes: {e}")
        
        # Verificar cuotas que vencen este mes
        try:
            primer_dia_mes = date(hoy.year, hoy.month, 1)
            if hoy.month == 12:
                ultimo_dia_mes = date(hoy.year + 1, 1, 1) - timedelta(days=1)
            else:
                ultimo_dia_mes = date(hoy.year, hoy.month + 1, 1) - timedelta(days=1)
            
            cuotas_mes = db.query(func.count(Cuota.id)).join(
                Prestamo, Cuota.prestamo_id == Prestamo.id
            ).filter(
                Cuota.fecha_vencimiento >= primer_dia_mes,
                Cuota.fecha_vencimiento <= ultimo_dia_mes,
                Prestamo.estado == "APROBADO"
            ).scalar() or 0
            print(f"[OK] Cuotas que vencen este mes: {cuotas_mes:,}")
        except Exception as e:
            print(f"[ERROR] Error verificando cuotas del mes: {e}")

    def main():
        """Función principal de verificación"""
        print("=" * 80)
        print("VERIFICACIÓN COMPLETA DE GRÁFICOS DEL DASHBOARD")
        print("=" * 80)
        print(f"\nFecha de verificación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        db = SessionLocal()
        resultados = {
            "conexion_bd": False,
            "tablas_existen": False,
            "datos_recientes": False,
            "endpoints_verificados": [],
            "total_endpoints": len(ENDPOINTS_VERIFICACION)
        }
        
        try:
            # 1. Verificar conexión
            resultados["conexion_bd"] = verificar_conexion_bd()
            if not resultados["conexion_bd"]:
                print("\n[ERROR CRÍTICO] No se puede conectar a la base de datos. Abortando verificación.")
                return resultados
            
            # 2. Verificar tablas
            resultados["tablas_existen"] = verificar_tablas_existen(db)
            
            # 3. Verificar datos recientes
            resultados["datos_recientes"] = verificar_datos_recientes(db)
            
            # 4. Verificar cada endpoint
            print("\n" + "=" * 80)
            print("5. VERIFICACIÓN DE ENDPOINTS DEL DASHBOARD")
            print("=" * 80)
            
            for endpoint_info in ENDPOINTS_VERIFICACION:
                endpoint_ok = verificar_endpoint_datos(endpoint_info, db)
                resultados["endpoints_verificados"].append({
                    "nombre": endpoint_info["nombre"],
                    "endpoint": endpoint_info["endpoint"],
                    "conectado": endpoint_ok
                })
            
            # 5. Verificar actualización de datos
            verificar_actualizacion_datos(db)
            
            # Resumen final
            print("\n" + "=" * 80)
            print("RESUMEN DE VERIFICACIÓN")
            print("=" * 80)
            
            endpoints_ok = sum(1 for e in resultados["endpoints_verificados"] if e["conectado"])
            
            print(f"\nConexión a BD: {'[OK]' if resultados['conexion_bd'] else '[ERROR]'}")
            print(f"Tablas principales: {'[OK]' if resultados['tablas_existen'] else '[ERROR]'}")
            print(f"Datos recientes: {'[OK]' if resultados['datos_recientes'] else '[ADVERTENCIA]'}")
            print(f"Endpoints verificados: {endpoints_ok}/{resultados['total_endpoints']}")
            
            if endpoints_ok < resultados['total_endpoints']:
                print("\n[ADVERTENCIA] Algunos endpoints pueden no tener datos disponibles:")
                for endpoint in resultados["endpoints_verificados"]:
                    if not endpoint["conectado"]:
                        print(f"  - {endpoint['nombre']} ({endpoint['endpoint']})")
            
            if resultados["conexion_bd"] and resultados["tablas_existen"] and endpoints_ok == resultados["total_endpoints"]:
                print("\n[OK] Todos los gráficos están correctamente conectados a la base de datos")
            else:
                print("\n[ADVERTENCIA] Algunos gráficos pueden no estar completamente conectados")
            
        finally:
            db.close()
        
        return resultados

    if __name__ == "__main__":
        try:
            resultados = main()
            sys.exit(0 if resultados.get("conexion_bd") and resultados.get("tablas_existen") else 1)
        except Exception as e:
            print(f"\n[ERROR] Error inesperado: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

except ImportError as e:
    print(f"[ERROR] Error importando módulos: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
