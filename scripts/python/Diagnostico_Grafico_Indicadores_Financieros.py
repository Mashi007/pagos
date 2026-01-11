"""
Script de diagnóstico para el gráfico "Indicadores Financieros"
Verifica por qué no muestra datos para Total Pagos Programados, Total Pagos Reales y Morosidad
"""

import os
import sys
from pathlib import Path
from datetime import date, datetime

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
    from app.db.session import SessionLocal
    from app.models.pago import Pago
    from app.models.prestamo import Prestamo
    from app.models.amortizacion import Cuota
    import logging

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    def diagnosticar_indicadores_financieros():
        """Diagnostica el gráfico de Indicadores Financieros"""
        print("=" * 80)
        print("DIAGNÓSTICO: GRÁFICO INDICADORES FINANCIEROS")
        print("=" * 80)
        
        hoy = date.today()
        print(f"\nFecha actual: {hoy}")
        print(f"Mes actual: {hoy.month}/{hoy.year}")
        
        db = SessionLocal()
        try:
            # Verificar datos para el mes actual (enero 2026)
            año_actual = hoy.year
            mes_actual = hoy.month
            
            print(f"\n{'='*80}")
            print(f"VERIFICANDO DATOS PARA: {mes_actual}/{año_actual}")
            print(f"{'='*80}")
            
            # 1. Verificar Total Financiamiento (préstamos aprobados en enero 2026)
            print("\n1. TOTAL FINANCIAMIENTO (Préstamos aprobados en enero 2026):")
            fecha_inicio_mes = date(año_actual, mes_actual, 1)
            if mes_actual == 12:
                fecha_fin_mes = date(año_actual + 1, 1, 1)
            else:
                fecha_fin_mes = date(año_actual, mes_actual + 1, 1)
            
            query_financiamiento = db.query(
                func.sum(Prestamo.total_financiamiento),
                func.count(Prestamo.id)
            ).filter(
                Prestamo.estado == "APROBADO",
                Prestamo.fecha_aprobacion >= fecha_inicio_mes,
                Prestamo.fecha_aprobacion < fecha_fin_mes
            )
            
            resultado_fin = query_financiamiento.first()
            total_fin = float(resultado_fin[0] or 0) if resultado_fin else 0
            cantidad_fin = resultado_fin[1] or 0 if resultado_fin else 0
            
            print(f"   Total Financiamiento: ${total_fin:,.2f}")
            print(f"   Cantidad de préstamos: {cantidad_fin}")
            
            # 2. Verificar Total Pagos Programados (cuotas que vencen en enero 2026)
            print("\n2. TOTAL PAGOS PROGRAMADOS (Cuotas que vencen en enero 2026):")
            query_cuotas = db.query(
                func.sum(Cuota.monto_cuota),
                func.count(Cuota.id)
            ).join(Prestamo, Cuota.prestamo_id == Prestamo.id).filter(
                Prestamo.estado == "APROBADO",
                func.extract("year", Cuota.fecha_vencimiento) == año_actual,
                func.extract("month", Cuota.fecha_vencimiento) == mes_actual
            )
            
            resultado_cuotas = query_cuotas.first()
            total_cuotas = float(resultado_cuotas[0] or 0) if resultado_cuotas else 0
            cantidad_cuotas = resultado_cuotas[1] or 0 if resultado_cuotas else 0
            
            print(f"   Total Cuotas Programadas: ${total_cuotas:,.2f}")
            print(f"   Cantidad de cuotas: {cantidad_cuotas}")
            
            # Verificar si hay cuotas con fecha_vencimiento en enero 2026
            query_cuotas_check = db.execute(text(f"""
                SELECT COUNT(*), MIN(fecha_vencimiento), MAX(fecha_vencimiento)
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE p.estado = 'APROBADO'
                  AND EXTRACT(YEAR FROM c.fecha_vencimiento) = {año_actual}
                  AND EXTRACT(MONTH FROM c.fecha_vencimiento) = {mes_actual}
            """))
            row_check = query_cuotas_check.fetchone()
            if row_check:
                print(f"   [DEBUG] Cuotas encontradas: {row_check[0]}")
                print(f"   [DEBUG] Fecha mínima: {row_check[1]}")
                print(f"   [DEBUG] Fecha máxima: {row_check[2]}")
            
            # 3. Verificar Total Pagos Reales (pagos en enero 2026)
            print("\n3. TOTAL PAGOS REALES (Pagos en enero 2026):")
            query_pagos = db.query(
                func.sum(Pago.monto_pagado),
                func.count(Pago.id)
            ).filter(
                Pago.activo.is_(True),
                Pago.monto_pagado.isnot(None),
                Pago.monto_pagado > 0,
                func.extract("year", Pago.fecha_pago) == año_actual,
                func.extract("month", Pago.fecha_pago) == mes_actual
            )
            
            resultado_pagos = query_pagos.first()
            total_pagos = float(resultado_pagos[0] or 0) if resultado_pagos else 0
            cantidad_pagos = resultado_pagos[1] or 0 if resultado_pagos else 0
            
            print(f"   Total Pagos Reales: ${total_pagos:,.2f}")
            print(f"   Cantidad de pagos: {cantidad_pagos}")
            
            # Verificar si hay pagos en enero 2026
            query_pagos_check = db.execute(text(f"""
                SELECT COUNT(*), MIN(fecha_pago), MAX(fecha_pago)
                FROM pagos
                WHERE activo = TRUE
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND EXTRACT(YEAR FROM fecha_pago) = {año_actual}
                  AND EXTRACT(MONTH FROM fecha_pago) = {mes_actual}
            """))
            row_pagos_check = query_pagos_check.fetchone()
            if row_pagos_check:
                print(f"   [DEBUG] Pagos encontrados: {row_pagos_check[0]}")
                print(f"   [DEBUG] Fecha mínima: {row_pagos_check[1]}")
                print(f"   [DEBUG] Fecha máxima: {row_pagos_check[2]}")
            
            # 4. Verificar Morosidad (cuotas vencidas no pagadas en enero 2026)
            print("\n4. MOROSIDAD (Cuotas que vencen en enero 2026 y NO fueron pagadas):")
            query_morosidad = db.execute(text(f"""
                SELECT 
                    COUNT(*) as cantidad_cuotas,
                    SUM(GREATEST(0, c.monto_cuota - COALESCE(c.total_pagado, 0))) as morosidad_total
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE p.estado = 'APROBADO'
                  AND EXTRACT(YEAR FROM c.fecha_vencimiento) = {año_actual}
                  AND EXTRACT(MONTH FROM c.fecha_vencimiento) = {mes_actual}
                  AND c.estado != 'PAGADO'
                  AND (c.monto_cuota - COALESCE(c.total_pagado, 0)) > 0
            """))
            row_morosidad = query_morosidad.fetchone()
            morosidad_total = float(row_morosidad[1] or 0) if row_morosidad else 0
            cantidad_morosidad = row_morosidad[0] or 0 if row_morosidad else 0
            
            print(f"   Total Morosidad: ${morosidad_total:,.2f}")
            print(f"   Cantidad de cuotas en mora: {cantidad_morosidad}")
            
            # 5. Verificar rango de fechas en las tablas
            print("\n5. RANGOS DE FECHAS EN LAS TABLAS:")
            
            # Fechas en préstamos
            query_fechas_prestamos = db.execute(text("""
                SELECT 
                    MIN(fecha_aprobacion) as fecha_min,
                    MAX(fecha_aprobacion) as fecha_max,
                    COUNT(*) as total
                FROM prestamos
                WHERE estado = 'APROBADO'
            """))
            row_prestamos = query_fechas_prestamos.fetchone()
            print(f"   Préstamos aprobados:")
            print(f"      Fecha mínima: {row_prestamos[0]}")
            print(f"      Fecha máxima: {row_prestamos[1]}")
            print(f"      Total: {row_prestamos[2]}")
            
            # Fechas en cuotas
            query_fechas_cuotas = db.execute(text("""
                SELECT 
                    MIN(c.fecha_vencimiento) as fecha_min,
                    MAX(c.fecha_vencimiento) as fecha_max,
                    COUNT(*) as total
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE p.estado = 'APROBADO'
            """))
            row_cuotas = query_fechas_cuotas.fetchone()
            print(f"   Cuotas (préstamos aprobados):")
            print(f"      Fecha vencimiento mínima: {row_cuotas[0]}")
            print(f"      Fecha vencimiento máxima: {row_cuotas[1]}")
            print(f"      Total: {row_cuotas[2]}")
            
            # Fechas en pagos
            query_fechas_pagos = db.execute(text("""
                SELECT 
                    MIN(fecha_pago) as fecha_min,
                    MAX(fecha_pago) as fecha_max,
                    COUNT(*) as total
                FROM pagos
                WHERE activo = TRUE
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
            """))
            row_pagos = query_fechas_pagos.fetchone()
            print(f"   Pagos activos:")
            print(f"      Fecha pago mínima: {row_pagos[0]}")
            print(f"      Fecha pago máxima: {row_pagos[1]}")
            print(f"      Total: {row_pagos[2]}")
            
            # Resumen
            print("\n" + "=" * 80)
            print("RESUMEN PARA ENERO 2026:")
            print("=" * 80)
            print(f"Total Financiamiento: ${total_fin:,.2f} ({cantidad_fin} préstamos)")
            print(f"Total Pagos Programados: ${total_cuotas:,.2f} ({cantidad_cuotas} cuotas)")
            print(f"Total Pagos Reales: ${total_pagos:,.2f} ({cantidad_pagos} pagos)")
            print(f"Morosidad: ${morosidad_total:,.2f} ({cantidad_morosidad} cuotas)")
            
            # Diagnóstico
            print("\n" + "=" * 80)
            print("DIAGNÓSTICO:")
            print("=" * 80)
            
            if total_cuotas == 0:
                print("[ADVERTENCIA] No hay cuotas programadas para enero 2026")
                print("   Posibles causas:")
                print("   - No hay cuotas que vencen en enero 2026")
                print("   - Las cuotas tienen fechas de vencimiento diferentes")
                print("   - Verificar rango de fechas en tabla cuotas")
            
            if total_pagos == 0:
                print("[ADVERTENCIA] No hay pagos registrados para enero 2026")
                print("   Posibles causas:")
                print("   - No se han registrado pagos en enero 2026 aún")
                print("   - Los pagos tienen fechas diferentes")
                print("   - Verificar rango de fechas en tabla pagos")
            
            if morosidad_total == 0 and total_cuotas > 0:
                print("[INFO] Morosidad en 0 puede ser normal si:")
                print("   - Todas las cuotas fueron pagadas completamente")
                print("   - Las cuotas aún no han vencido")
                print("   - Las cuotas están en estado PAGADO")
            
            if total_fin > 0 and total_cuotas == 0 and total_pagos == 0:
                print("\n[CONCLUSIÓN] El gráfico muestra Total Financiamiento porque hay préstamos aprobados,")
                print("pero no hay cuotas ni pagos para enero 2026. Esto es normal si:")
                print("   - Estamos a principios de mes")
                print("   - Las cuotas vencen más adelante en el mes")
                print("   - Aún no se han registrado pagos este mes")
            
        finally:
            db.close()

    if __name__ == "__main__":
        try:
            diagnosticar_indicadores_financieros()
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
