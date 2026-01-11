"""
Script para probar el endpoint de Indicadores Financieros y ver qué retorna
"""

import os
import sys
from pathlib import Path
from datetime import date

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from app.db.session import SessionLocal
    from app.api.v1.endpoints.dashboard import (
        _obtener_nuevos_financiamientos_por_mes,
        _obtener_cuotas_programadas_por_mes,
        _obtener_pagos_por_mes,
        _obtener_morosidad_por_mes,
        _generar_datos_mensuales,
        _obtener_fecha_inicio_query
    )
    from app.core.cache import cache_backend
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def test_endpoint():
        """Prueba el endpoint de Indicadores Financieros"""
        print("=" * 80)
        print("PRUEBA DEL ENDPOINT: Indicadores Financieros")
        print("=" * 80)
        
        db = SessionLocal()
        try:
            hoy = date.today()
            print(f"\nFecha actual: {hoy}")
            
            # Simular llamada al endpoint sin filtros
            fecha_inicio = None
            fecha_fin = None
            analista = None
            concesionario = None
            modelo = None
            
            # Obtener fecha_inicio_query
            fecha_inicio_query = _obtener_fecha_inicio_query(db, fecha_inicio, cache_backend)
            fecha_fin_query = hoy
            
            print(f"\nFechas de query:")
            print(f"   fecha_inicio_query: {fecha_inicio_query}")
            print(f"   fecha_fin_query: {fecha_fin_query}")
            
            # Llamar a las funciones helper
            print("\n" + "=" * 80)
            print("1. Obteniendo nuevos financiamientos por mes...")
            nuevos_por_mes = _obtener_nuevos_financiamientos_por_mes(
                db, fecha_inicio_query, fecha_fin_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
            print(f"   Resultado: {len(nuevos_por_mes)} meses con datos")
            if nuevos_por_mes:
                print(f"   Ejemplo (últimos 3): {list(nuevos_por_mes.items())[-3:]}")
            
            print("\n2. Obteniendo cuotas programadas por mes...")
            cuotas_por_mes = _obtener_cuotas_programadas_por_mes(
                db, analista, concesionario, modelo, fecha_inicio_query, fecha_fin_query
            )
            print(f"   Resultado: {len(cuotas_por_mes)} meses con datos")
            if cuotas_por_mes:
                print(f"   Ejemplo (últimos 3): {list(cuotas_por_mes.items())[-3:]}")
                # Verificar específicamente enero 2026
                enero_2026 = cuotas_por_mes.get((2026, 1), 0)
                print(f"   Enero 2026: ${enero_2026:,.2f}")
            
            print("\n3. Obteniendo pagos por mes...")
            pagos_por_mes = _obtener_pagos_por_mes(
                db, fecha_inicio_query, fecha_fin_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
            print(f"   Resultado: {len(pagos_por_mes)} meses con datos")
            if pagos_por_mes:
                print(f"   Ejemplo (últimos 3): {list(pagos_por_mes.items())[-3:]}")
                # Verificar específicamente enero 2026
                enero_2026 = pagos_por_mes.get((2026, 1), 0)
                print(f"   Enero 2026: ${enero_2026:,.2f}")
            
            print("\n4. Obteniendo morosidad por mes...")
            morosidad_por_mes = _obtener_morosidad_por_mes(
                db, analista, concesionario, modelo, fecha_inicio_query, fecha_fin_query
            )
            print(f"   Resultado: {len(morosidad_por_mes)} meses con datos")
            if morosidad_por_mes:
                print(f"   Ejemplo (últimos 3): {list(morosidad_por_mes.items())[-3:]}")
                # Verificar específicamente enero 2026
                enero_2026 = morosidad_por_mes.get((2026, 1), 0)
                print(f"   Enero 2026: ${enero_2026:,.2f}")
            
            print("\n5. Generando datos mensuales...")
            meses_data = _generar_datos_mensuales(
                fecha_inicio_query, hoy, nuevos_por_mes, cuotas_por_mes, pagos_por_mes, morosidad_por_mes
            )
            print(f"   Resultado: {len(meses_data)} meses generados")
            
            # Buscar enero 2026 en los datos
            enero_2026_data = None
            for mes_data in meses_data:
                if "Ene 2026" in mes_data.get("mes", ""):
                    enero_2026_data = mes_data
                    break
            
            if enero_2026_data:
                print("\n" + "=" * 80)
                print("DATOS PARA ENERO 2026:")
                print("=" * 80)
                print(f"   Mes: {enero_2026_data.get('mes')}")
                print(f"   Total Financiamiento (monto_nuevos): ${enero_2026_data.get('monto_nuevos', 0):,.2f}")
                print(f"   Total Pagos Programados (monto_cuotas_programadas): ${enero_2026_data.get('monto_cuotas_programadas', 0):,.2f}")
                print(f"   Total Pagos Reales (monto_pagado): ${enero_2026_data.get('monto_pagado', 0):,.2f}")
                print(f"   Morosidad (morosidad_mensual): ${enero_2026_data.get('morosidad_mensual', 0):,.2f}")
            else:
                print("\n[ADVERTENCIA] No se encontró enero 2026 en los datos generados")
                if meses_data:
                    print(f"   Últimos 3 meses generados:")
                    for mes_data in meses_data[-3:]:
                        print(f"      {mes_data.get('mes')}: Financiamiento=${mes_data.get('monto_nuevos', 0):,.2f}, "
                              f"Programados=${mes_data.get('monto_cuotas_programadas', 0):,.2f}, "
                              f"Reales=${mes_data.get('monto_pagado', 0):,.2f}, "
                              f"Morosidad=${mes_data.get('morosidad_mensual', 0):,.2f}")
            
        finally:
            db.close()

    if __name__ == "__main__":
        try:
            test_endpoint()
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
