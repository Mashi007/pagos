#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mostrar dónde se refleja el total de abonos por cédula"""

import sys
from pathlib import Path
from decimal import Decimal

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
try:
    print("="*80)
    print("DONDE SE REFLEJA EL TOTAL DE ABONOS POR CEDULA")
    print("="*80)
    
    # 1. Desde tabla pagos (pagos conciliados)
    print("\n[1] TABLA pagos - Total de abonos por cédula (pagos conciliados)")
    print("-" * 80)
    print("Consulta SQL:")
    print("""
    SELECT 
        cedula,
        COUNT(*) as cantidad_pagos,
        SUM(monto_pagado) as total_abonos
    FROM pagos
    WHERE (conciliado = TRUE OR verificado_concordancia = 'SI')
      AND prestamo_id IS NOT NULL
    GROUP BY cedula
    ORDER BY total_abonos DESC
    """)
    
    query_pagos = text("""
        SELECT 
            cedula,
            COUNT(*) as cantidad_pagos,
            SUM(monto_pagado) as total_abonos
        FROM pagos
        WHERE (conciliado = TRUE OR verificado_concordancia = 'SI')
          AND prestamo_id IS NOT NULL
        GROUP BY cedula
        ORDER BY total_abonos DESC
        LIMIT 10
    """)
    result_pagos = db.execute(query_pagos)
    pagos_rows = result_pagos.fetchall()
    
    print("\nEjemplos (Top 10):")
    print(f"{'Cédula':<15} {'Cantidad Pagos':<18} {'Total Abonos':<20}")
    print("-" * 53)
    for row in pagos_rows:
        print(f"{row[0]:<15} {row[1]:>16,}  Bs. {float(row[2]):>15,.2f}")
    
    # 2. Desde tabla cuotas (total_pagado acumulado)
    print("\n[2] TABLA cuotas - Total de abonos por cédula (suma de total_pagado)")
    print("-" * 80)
    print("Consulta SQL:")
    print("""
    SELECT 
        p.cedula,
        COUNT(DISTINCT c.prestamo_id) as cantidad_prestamos,
        COUNT(c.id) as cantidad_cuotas_con_pagos,
        SUM(c.total_pagado) as total_abonos
    FROM cuotas c
    INNER JOIN prestamos p ON p.id = c.prestamo_id
    WHERE c.total_pagado > 0
    GROUP BY p.cedula
    ORDER BY total_abonos DESC
    """)
    
    query_cuotas = text("""
        SELECT 
            p.cedula,
            COUNT(DISTINCT c.prestamo_id) as cantidad_prestamos,
            COUNT(c.id) as cantidad_cuotas_con_pagos,
            SUM(c.total_pagado) as total_abonos
        FROM cuotas c
        INNER JOIN prestamos p ON p.id = c.prestamo_id
        WHERE c.total_pagado > 0
        GROUP BY p.cedula
        ORDER BY total_abonos DESC
        LIMIT 10
    """)
    result_cuotas = db.execute(query_cuotas)
    cuotas_rows = result_cuotas.fetchall()
    
    print("\nEjemplos (Top 10):")
    print(f"{'Cédula':<15} {'Préstamos':<12} {'Cuotas':<12} {'Total Abonos':<20}")
    print("-" * 59)
    for row in cuotas_rows:
        print(f"{row[0]:<15} {row[1]:>10}  {row[2]:>10}  Bs. {float(row[3]):>15,.2f}")
    
    # 3. Comparación entre ambas fuentes
    print("\n[3] COMPARACION: pagos vs cuotas (para verificar consistencia)")
    print("-" * 80)
    
    query_comparacion = text("""
        SELECT 
            COALESCE(p.cedula, c.cedula) as cedula,
            COALESCE(SUM(p.monto_pagado), 0) as total_desde_pagos,
            COALESCE(SUM(c.total_pagado), 0) as total_desde_cuotas,
            ABS(COALESCE(SUM(p.monto_pagado), 0) - COALESCE(SUM(c.total_pagado), 0)) as diferencia
        FROM (
            SELECT cedula, SUM(monto_pagado) as monto_pagado
            FROM pagos
            WHERE (conciliado = TRUE OR verificado_concordancia = 'SI')
              AND prestamo_id IS NOT NULL
            GROUP BY cedula
        ) p
        FULL OUTER JOIN (
            SELECT p.cedula, SUM(c.total_pagado) as total_pagado
            FROM cuotas c
            INNER JOIN prestamos p ON p.id = c.prestamo_id
            WHERE c.total_pagado > 0
            GROUP BY p.cedula
        ) c ON p.cedula = c.cedula
        GROUP BY COALESCE(p.cedula, c.cedula)
        HAVING ABS(COALESCE(SUM(p.monto_pagado), 0) - COALESCE(SUM(c.total_pagado), 0)) > 0.01
        ORDER BY diferencia DESC
        LIMIT 10
    """)
    result_comparacion = db.execute(query_comparacion)
    comparacion_rows = result_comparacion.fetchall()
    
    if comparacion_rows:
        print("Cédulas con diferencias:")
        print(f"{'Cédula':<15} {'Desde pagos':<18} {'Desde cuotas':<18} {'Diferencia':<15}")
        print("-" * 66)
        for row in comparacion_rows:
            print(f"{row[0]:<15} Bs. {float(row[1]):>15,.2f} Bs. {float(row[2]):>15,.2f} Bs. {float(row[3]):>12,.2f}")
    else:
        print("[OK] No hay diferencias significativas entre ambas fuentes")
    
    # 4. Resumen general
    print("\n[4] RESUMEN GENERAL")
    print("-" * 80)
    
    query_resumen = text("""
        SELECT 
            (SELECT COUNT(DISTINCT cedula) FROM pagos 
             WHERE (conciliado = TRUE OR verificado_concordancia = 'SI') 
               AND prestamo_id IS NOT NULL) as cedulas_con_pagos_conciliados,
            (SELECT SUM(monto_pagado) FROM pagos 
             WHERE (conciliado = TRUE OR verificado_concordancia = 'SI') 
               AND prestamo_id IS NOT NULL) as total_abonos_desde_pagos,
            (SELECT COUNT(DISTINCT p.cedula) FROM cuotas c
             INNER JOIN prestamos p ON p.id = c.prestamo_id
             WHERE c.total_pagado > 0) as cedulas_con_pagos_en_cuotas,
            (SELECT SUM(c.total_pagado) FROM cuotas c
             INNER JOIN prestamos p ON p.id = c.prestamo_id
             WHERE c.total_pagado > 0) as total_abonos_desde_cuotas
    """)
    result_resumen = db.execute(query_resumen)
    resumen = result_resumen.fetchone()
    
    cedulas_pagos = resumen[0] if resumen[0] else 0
    total_pagos = Decimal(str(resumen[1])) if resumen[1] else Decimal("0")
    cedulas_cuotas = resumen[2] if resumen[2] else 0
    total_cuotas = Decimal(str(resumen[3])) if resumen[3] else Decimal("0")
    
    print(f"Cédulas con pagos conciliados (desde pagos): {cedulas_pagos:,}")
    print(f"Total abonos desde pagos: Bs. {total_pagos:,.2f}")
    print(f"\nCédulas con pagos aplicados (desde cuotas): {cedulas_cuotas:,}")
    print(f"Total abonos desde cuotas: Bs. {total_cuotas:,.2f}")
    
    diferencia = abs(total_pagos - total_cuotas)
    print(f"\nDiferencia: Bs. {diferencia:,.2f}")
    
    # 5. Conclusión
    print("\n" + "="*80)
    print("CONCLUSION: DONDE SE REFLEJA EL TOTAL DE ABONOS POR CEDULA")
    print("="*80)
    
    print("\n[RESPUESTA] El total de abonos por cédula se refleja en DOS lugares:")
    print("\n1. TABLA pagos (fuente primaria):")
    print("   - Columna: monto_pagado")
    print("   - Filtro: conciliado = TRUE O verificado_concordancia = 'SI'")
    print("   - Agrupación: GROUP BY cedula")
    print("   - Cálculo: SUM(monto_pagado) por cedula")
    print("   - Consulta:")
    print("     SELECT cedula, SUM(monto_pagado) as total_abonos")
    print("     FROM pagos")
    print("     WHERE (conciliado = TRUE OR verificado_concordancia = 'SI')")
    print("       AND prestamo_id IS NOT NULL")
    print("     GROUP BY cedula")
    
    print("\n2. TABLA cuotas (reflejo aplicado):")
    print("   - Columna: total_pagado")
    print("   - Relación: cuotas -> prestamos -> cedula")
    print("   - Agrupación: GROUP BY prestamos.cedula")
    print("   - Cálculo: SUM(total_pagado) por cedula")
    print("   - Consulta:")
    print("     SELECT p.cedula, SUM(c.total_pagado) as total_abonos")
    print("     FROM cuotas c")
    print("     INNER JOIN prestamos p ON p.id = c.prestamo_id")
    print("     WHERE c.total_pagado > 0")
    print("     GROUP BY p.cedula")
    
    print("\n[NOTA IMPORTANTE]:")
    print("   - La tabla pagos contiene los pagos individuales conciliados")
    print("   - La tabla cuotas contiene el total acumulado aplicado a cada cuota")
    print("   - Ambos deberían coincidir si los pagos se aplicaron correctamente")
    print("   - La diferencia puede existir si hay pagos que aún no se aplicaron a cuotas")
    
    print("\n" + "="*80)
    
finally:
    db.close()
