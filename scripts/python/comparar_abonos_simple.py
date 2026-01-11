#!/usr/bin/env python3
"""
Script simple para comparar abonos entre BD y abono_2026.
Muestra: cedula, abonos_bd, abonos_2026, diferencia
"""

import sys
from pathlib import Path
from decimal import Decimal

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db.session import SessionLocal

def main():
    print("=" * 80)
    print("COMPARACION: Abonos BD vs abono_2026")
    print("=" * 80)
    print()
    
    db = SessionLocal()
    
    try:
        # Query de comparación
        query = text("""
            WITH abonos_bd AS (
                SELECT 
                    p.cedula,
                    COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd
                FROM prestamos p
                LEFT JOIN cuotas c ON p.id = c.prestamo_id
                WHERE p.cedula IS NOT NULL
                  AND p.cedula != ''
                GROUP BY p.cedula
            ),
            abonos_2026 AS (
                SELECT 
                    cedula,
                    COALESCE(SUM(abonos)::numeric, 0) AS total_abonos_2026
                FROM abono_2026
                WHERE cedula IS NOT NULL
                GROUP BY cedula
            )
            SELECT 
                COALESCE(bd.cedula, t2026.cedula) AS cedula,
                COALESCE(bd.total_abonos_bd, 0) AS abonos_bd,
                COALESCE(t2026.total_abonos_2026, 0) AS abonos_2026,
                ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) AS diferencia,
                CASE 
                    WHEN bd.cedula IS NULL THEN 'Solo en abono_2026'
                    WHEN t2026.cedula IS NULL THEN 'Solo en BD'
                    WHEN ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) <= 0.01 THEN 'Coincide'
                    ELSE 'Diferencia'
                END AS estado
            FROM abonos_bd bd
            FULL OUTER JOIN abonos_2026 t2026 ON bd.cedula = t2026.cedula
            ORDER BY diferencia DESC, cedula
        """)
        
        resultado = db.execute(query)
        
        # Encabezado
        print(f"{'Cedula':<20} {'Abonos BD':>15} {'Abonos 2026':>15} {'Diferencia':>15} {'Estado':<20}")
        print("-" * 85)
        
        total_registros = 0
        coincidencias = 0
        discrepancias = 0
        total_bd = Decimal("0")
        total_2026 = Decimal("0")
        
        # Mostrar TODAS las cédulas sin filtrar
        for row in resultado:
            cedula = str(row[0])
            abonos_bd = Decimal(str(row[1]))
            abonos_2026 = Decimal(str(row[2]))
            diferencia = Decimal(str(row[3]))
            estado = str(row[4])
            
            total_registros += 1
            total_bd += abonos_bd
            total_2026 += abonos_2026
            
            if estado == 'Coincide':
                coincidencias += 1
            else:
                discrepancias += 1
            
            # Mostrar TODAS las cédulas sin discriminar
            print(f"{cedula:<20} ${abonos_bd:>14,.2f} ${abonos_2026:>14,.2f} ${diferencia:>14,.2f} {estado:<20}")
        
        print("-" * 85)
        print()
        print("RESUMEN:")
        print(f"  Total cédulas: {total_registros:,}")
        print(f"  Coincidencias: {coincidencias:,} ({coincidencias*100/total_registros:.1f}%)")
        print(f"  Discrepancias: {discrepancias:,} ({discrepancias*100/total_registros:.1f}%)")
        print(f"  Total abonos BD: ${total_bd:,.2f}")
        print(f"  Total abonos 2026: ${total_2026:,.2f}")
        print(f"  Diferencia total: ${abs(total_bd - total_2026):,.2f}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
