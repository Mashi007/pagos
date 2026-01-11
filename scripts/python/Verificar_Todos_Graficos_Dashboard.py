"""
Script para verificar que todos los gráficos del dashboard estén conectados correctamente a la base de datos
"""

import os
import sys
from pathlib import Path
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
    from sqlalchemy import text, inspect
    from app.db.session import SessionLocal, engine, get_db, test_connection
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

    # Lista de endpoints del dashboard a verificar
    ENDPOINTS_DASHBOARD = {
        "/api/v1/dashboard/opciones-filtros": {
            "descripcion": "Opciones de filtros (analistas, concesionarios, modelos)",
            "tablas": ["prestamos"],
            "campos": ["analista", "producto_financiero", "concesionario", "producto", "modelo_vehiculo"]
        },
        "/api/v1/dashboard/kpis-principales": {
            "descripcion": "KPIs principales del dashboard",
            "tablas": ["prestamos", "cuotas", "pagos"],
            "campos": ["total_financiamiento", "fecha_aprobacion", "estado", "monto_cuota", "fecha_vencimiento", "monto_pagado", "fecha_pago"]
        },
        "/api/v1/dashboard/admin": {
            "descripcion": "Dashboard administrativo completo",
            "tablas": ["prestamos", "pagos", "cuotas"],
            "campos": ["total_financiamiento", "fecha_aprobacion", "monto_pagado", "fecha_pago", "monto_cuota", "fecha_vencimiento"]
        },
        "/api/v1/dashboard/financiamiento-tendencia-mensual": {
            "descripcion": "Tendencia mensual de financiamientos (Indicadores Financieros)",
            "tablas": ["prestamos", "cuotas", "pagos"],
            "campos": ["fecha_aprobacion", "total_financiamiento", "fecha_vencimiento", "monto_cuota", "fecha_pago", "monto_pagado"]
        },
        "/api/v1/dashboard/prestamos-por-concesionario": {
            "descripcion": "Préstamos agrupados por concesionario",
            "tablas": ["prestamos"],
            "campos": ["concesionario", "total_financiamiento", "estado"]
        },
        "/api/v1/dashboard/prestamos-por-modelo": {
            "descripcion": "Préstamos agrupados por modelo",
            "tablas": ["prestamos"],
            "campos": ["producto", "modelo_vehiculo", "total_financiamiento", "estado"]
        },
        "/api/v1/dashboard/financiamiento-por-rangos": {
            "descripcion": "Financiamiento por rangos de monto",
            "tablas": ["prestamos"],
            "campos": ["total_financiamiento", "estado"]
        },
        "/api/v1/dashboard/composicion-morosidad": {
            "descripcion": "Composición de morosidad",
            "tablas": ["cuotas", "prestamos"],
            "campos": ["fecha_vencimiento", "monto_cuota", "total_pagado", "estado"]
        },
        "/api/v1/dashboard/cobranzas-mensuales": {
            "descripcion": "Cobranzas mensuales",
            "tablas": ["cuotas", "pagos", "prestamos"],
            "campos": ["fecha_vencimiento", "monto_cuota", "fecha_pago", "monto_pagado"]
        },
        "/api/v1/dashboard/cobranza-fechas-especificas": {
            "descripcion": "Cobranza por fechas específicas",
            "tablas": ["pagos"],
            "campos": ["fecha_pago", "monto_pagado", "activo"]
        },
        "/api/v1/dashboard/cobranzas-semanales": {
            "descripcion": "Cobranzas semanales",
            "tablas": ["pagos", "prestamos"],
            "campos": ["fecha_pago", "monto_pagado", "activo"]
        },
        "/api/v1/dashboard/morosidad-por-analista": {
            "descripcion": "Morosidad agrupada por analista",
            "tablas": ["cuotas", "prestamos"],
            "campos": ["analista", "fecha_vencimiento", "monto_cuota", "total_pagado", "estado"]
        },
        "/api/v1/dashboard/evolucion-morosidad": {
            "descripcion": "Evolución de morosidad mensual",
            "tablas": ["cuotas", "prestamos"],
            "campos": ["fecha_vencimiento", "monto_cuota", "total_pagado", "estado"]
        },
        "/api/v1/dashboard/evolucion-pagos": {
            "descripcion": "Evolución de pagos mensual",
            "tablas": ["pagos"],
            "campos": ["fecha_pago", "monto_pagado", "activo"]
        },
        "/api/v1/dashboard/evolucion-general-mensual": {
            "descripcion": "Evolución general mensual (Cartera, Cobrado, Morosidad)",
            "tablas": ["prestamos", "pagos", "cuotas"],
            "campos": ["fecha_registro", "total_financiamiento", "fecha_pago", "monto_pagado", "fecha_vencimiento", "monto_cuota"]
        },
        "/api/v1/dashboard/cobros-diarios": {
            "descripcion": "Cobros diarios",
            "tablas": ["pagos", "cuotas", "prestamos"],
            "campos": ["fecha_pago", "monto_pagado", "fecha_vencimiento", "monto_cuota"]
        },
        "/api/v1/dashboard/distribucion-prestamos": {
            "descripcion": "Distribución de préstamos",
            "tablas": ["prestamos"],
            "campos": ["total_financiamiento", "estado", "plazo_meses"]
        },
        "/api/v1/dashboard/cuentas-cobrar-tendencias": {
            "descripcion": "Tendencias de cuentas por cobrar",
            "tablas": ["cuotas", "prestamos"],
            "campos": ["fecha_vencimiento", "monto_cuota", "total_pagado", "estado"]
        },
        "/api/v1/dashboard/metricas-acumuladas": {
            "descripcion": "Métricas acumuladas",
            "tablas": ["prestamos", "pagos", "cuotas"],
            "campos": ["total_financiamiento", "monto_pagado", "monto_cuota"]
        },
        "/api/v1/dashboard/pagos-conciliados": {
            "descripcion": "Pagos conciliados",
            "tablas": ["pagos", "cuotas"],
            "campos": ["fecha_pago", "monto_pagado", "estado"]
        },
        "/api/v1/dashboard/analista": {
            "descripcion": "Dashboard por analista",
            "tablas": ["prestamos", "pagos", "cuotas"],
            "campos": ["analista", "total_financiamiento", "monto_pagado", "monto_cuota"]
        },
        "/api/v1/dashboard/resumen": {
            "descripcion": "Resumen del dashboard",
            "tablas": ["prestamos", "pagos", "cuotas"],
            "campos": ["total_financiamiento", "monto_pagado", "monto_cuota", "estado"]
        },
    }

    def verificar_tabla_existe(db, nombre_tabla: str) -> bool:
        """Verifica si una tabla existe en la base de datos"""
        try:
            inspector = inspect(db.bind)
            tablas = inspector.get_table_names()
            return nombre_tabla.lower() in [t.lower() for t in tablas]
        except Exception as e:
            logger.error(f"Error verificando tabla {nombre_tabla}: {e}")
            return False

    def verificar_campos_tabla(db, nombre_tabla: str, campos: List[str]) -> Dict[str, bool]:
        """Verifica si los campos existen en una tabla"""
        resultados = {}
        try:
            inspector = inspect(db.bind)
            columnas = inspector.get_columns(nombre_tabla)
            nombres_columnas = [col["name"].lower() for col in columnas]
            
            for campo in campos:
                # Remover prefijo de tabla si existe (ej: "prestamos.total_financiamiento" -> "total_financiamiento")
                campo_limpio = campo.split(".")[-1].lower()
                resultados[campo] = campo_limpio in nombres_columnas
            
            return resultados
        except Exception as e:
            logger.error(f"Error verificando campos de tabla {nombre_tabla}: {e}")
            return {campo: False for campo in campos}

    def verificar_query_basica(db, nombre_tabla: str) -> bool:
        """Verifica que se pueda hacer una query básica a una tabla"""
        try:
            query = text(f"SELECT COUNT(*) FROM {nombre_tabla} LIMIT 1")
            result = db.execute(query)
            result.scalar()
            return True
        except Exception as e:
            logger.error(f"Error en query básica a {nombre_tabla}: {e}")
            return False

    def verificar_endpoint(endpoint_info: Dict[str, Any], db) -> Dict[str, Any]:
        """Verifica un endpoint del dashboard"""
        resultado = {
            "endpoint": endpoint_info.get("endpoint", ""),
            "descripcion": endpoint_info.get("descripcion", ""),
            "tablas_ok": [],
            "tablas_faltantes": [],
            "campos_ok": {},
            "campos_faltantes": {},
            "queries_ok": {},
            "queries_fallidas": {},
            "estado_general": "ok"
        }
        
        tablas = endpoint_info.get("tablas", [])
        campos = endpoint_info.get("campos", [])
        
        # Verificar tablas
        for tabla in tablas:
            if verificar_tabla_existe(db, tabla):
                resultado["tablas_ok"].append(tabla)
                # Verificar campos de esta tabla (todos los campos que mencionan esta tabla)
                campos_tabla = []
                for campo in campos:
                    # Si el campo tiene prefijo de tabla, verificar que coincida
                    if "." in campo:
                        tabla_campo = campo.split(".")[0].lower()
                        if tabla_campo == tabla.lower():
                            campos_tabla.append(campo)
                    else:
                        # Si no tiene prefijo, asumir que es de esta tabla
                        campos_tabla.append(campo)
                
                if campos_tabla:
                    campos_verificados = verificar_campos_tabla(db, tabla, campos_tabla)
                    resultado["campos_ok"][tabla] = [c for c, ok in campos_verificados.items() if ok]
                    resultado["campos_faltantes"][tabla] = [c for c, ok in campos_verificados.items() if not ok]
                
                # Verificar query básica
                if verificar_query_basica(db, tabla):
                    resultado["queries_ok"][tabla] = True
                else:
                    resultado["queries_fallidas"][tabla] = True
                    resultado["estado_general"] = "error"
            else:
                resultado["tablas_faltantes"].append(tabla)
                resultado["estado_general"] = "error"
        
        # Si faltan tablas críticas, marcar como error
        if resultado["tablas_faltantes"]:
            resultado["estado_general"] = "error"
        
        return resultado

    def verificar_todos_graficos():
        """Verifica todos los gráficos del dashboard"""
        print("=" * 80)
        print("VERIFICACIÓN COMPLETA DE GRÁFICOS DEL DASHBOARD")
        print("=" * 80)
        
        # Verificar conexión básica
        print("\n1. Verificando conexión básica a la base de datos...")
        if not test_connection():
            print("   [ERROR] No se puede conectar a la base de datos")
            return
        
        print("   [OK] Conexión básica exitosa")
        
        # Verificar tablas principales
        print("\n2. Verificando tablas principales...")
        db = SessionLocal()
        try:
            tablas_principales = ['pagos', 'prestamos', 'cuotas', 'clientes']
            for tabla in tablas_principales:
                if verificar_tabla_existe(db, tabla):
                    count_query = text(f"SELECT COUNT(*) FROM {tabla}")
                    count = db.execute(count_query).scalar()
                    print(f"   [OK] Tabla '{tabla}' existe - {count} registros")
                else:
                    print(f"   [ERROR] Tabla '{tabla}' NO existe")
        finally:
            db.close()
        
        # Verificar cada endpoint
        print("\n3. Verificando endpoints del dashboard...")
        resultados_endpoints = []
        
        db = SessionLocal()
        try:
            for endpoint_path, endpoint_info in ENDPOINTS_DASHBOARD.items():
                endpoint_info["endpoint"] = endpoint_path
                print(f"\n   Verificando: {endpoint_path}")
                print(f"   Descripción: {endpoint_info['descripcion']}")
                
                resultado = verificar_endpoint(endpoint_info, db)
                resultados_endpoints.append(resultado)
                
                # Mostrar resumen del endpoint
                if resultado["estado_general"] == "ok":
                    print(f"   [OK] Endpoint conectado correctamente")
                    print(f"      Tablas: {', '.join(resultado['tablas_ok'])}")
                else:
                    print(f"   [ERROR] Endpoint con problemas")
                    if resultado["tablas_faltantes"]:
                        print(f"      Tablas faltantes: {', '.join(resultado['tablas_faltantes'])}")
                    if resultado["queries_fallidas"]:
                        print(f"      Queries fallidas: {', '.join(resultado['queries_fallidas'].keys())}")
        finally:
            db.close()
        
        # Resumen final
        print("\n" + "=" * 80)
        print("RESUMEN DE VERIFICACIÓN")
        print("=" * 80)
        
        total_endpoints = len(resultados_endpoints)
        endpoints_ok = sum(1 for r in resultados_endpoints if r["estado_general"] == "ok")
        endpoints_error = total_endpoints - endpoints_ok
        
        print(f"\nTotal endpoints verificados: {total_endpoints}")
        print(f"Endpoints OK: {endpoints_ok}")
        print(f"Endpoints con errores: {endpoints_error}")
        
        print("\nDetalle por endpoint:")
        for resultado in resultados_endpoints:
            estado = "[OK]" if resultado["estado_general"] == "ok" else "[ERROR]"
            print(f"\n{estado} {resultado['endpoint']}")
            print(f"   Descripción: {resultado['descripcion']}")
            print(f"   Tablas OK: {len(resultado['tablas_ok'])}/{len(resultado.get('tablas', []))}")
            
            if resultado["tablas_faltantes"]:
                print(f"   [ERROR] Tablas faltantes: {', '.join(resultado['tablas_faltantes'])}")
            
            if resultado["campos_faltantes"]:
                for tabla, campos in resultado["campos_faltantes"].items():
                    if campos:
                        print(f"   [ADVERTENCIA] Campos faltantes en {tabla}: {', '.join(campos)}")
            
            if resultado["queries_fallidas"]:
                print(f"   [ERROR] Queries fallidas: {', '.join(resultado['queries_fallidas'].keys())}")
        
        # Endpoints con problemas críticos
        endpoints_criticos = [r for r in resultados_endpoints if r["estado_general"] == "error"]
        if endpoints_criticos:
            print("\n" + "=" * 80)
            print("ENDPOINTS CON PROBLEMAS CRÍTICOS")
            print("=" * 80)
            for resultado in endpoints_criticos:
                print(f"\n[ERROR] {resultado['endpoint']}")
                print(f"   {resultado['descripcion']}")
                if resultado["tablas_faltantes"]:
                    print(f"   Tablas faltantes: {', '.join(resultado['tablas_faltantes'])}")
                if resultado["queries_fallidas"]:
                    print(f"   Queries fallidas: {', '.join(resultado['queries_fallidas'].keys())}")
        
        return resultados_endpoints

    if __name__ == "__main__":
        try:
            resultados = verificar_todos_graficos()
            
            # Contar endpoints con errores
            endpoints_error = sum(1 for r in resultados if r["estado_general"] == "error")
            
            if endpoints_error > 0:
                print(f"\n[ADVERTENCIA] {endpoints_error} endpoints tienen problemas")
                sys.exit(1)
            else:
                print("\n[EXITO] Todos los endpoints están conectados correctamente")
                sys.exit(0)
        except Exception as e:
            print(f"\n[ERROR] Error inesperado: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

except ImportError as e:
    print(f"[ERROR] Error importando módulos: {e}")
    print("Asegúrate de ejecutar este script desde la raíz del proyecto")
    import traceback
    traceback.print_exc()
    sys.exit(1)
