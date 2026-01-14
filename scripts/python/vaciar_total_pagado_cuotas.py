#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para limpiar la columna total_pagado en tabla cuotas.

Este script:
- Establece total_pagado = 0.00 en TODAS las cuotas
- Limpia fecha_pago
- Actualiza el estado de las cuotas según fecha_vencimiento
- Crea backup antes de limpiar

⚠️ ADVERTENCIA: Este script elimina TODOS los datos de pagos en cuotas.
Solo ejecutar si estás seguro de que quieres empezar desde cero.

Uso:
    python scripts/python/vaciar_total_pagado_cuotas.py [--yes]
"""

import sys
import argparse
from pathlib import Path
from datetime import date
from decimal import Decimal

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text, func
from app.db.session import SessionLocal
from app.models.amortizacion import Cuota
from app.models.prestamo import Prestamo


def crear_backup(db):
    """Crea backup de cuotas con total_pagado > 0"""
    print("Creando backup de cuotas con total_pagado > 0...")
    
    try:
        query_backup = text("""
            CREATE TABLE IF NOT EXISTS cuotas_backup_total_pagado AS
            SELECT 
                id,
                prestamo_id,
                numero_cuota,
                total_pagado,
                fecha_pago,
                estado,
                monto_cuota,
                fecha_vencimiento,
                NOW() AS fecha_backup
            FROM cuotas
            WHERE total_pagado > 0 OR fecha_pago IS NOT NULL
        """)
        
        db.execute(query_backup)
        db.commit()
        
        # Contar registros en backup
        query_count = text("SELECT COUNT(*) FROM cuotas_backup_total_pagado")
        count = db.execute(query_count).scalar() or 0
        
        print(f"  Backup creado: {count} registros guardados en tabla cuotas_backup_total_pagado")
        return True
        
    except Exception as e:
        print(f"  [ERROR] Error creando backup: {str(e)}")
        db.rollback()
        return False


def verificar_antes_de_limpiar(db):
    """Verifica cuántas cuotas se van a limpiar"""
    print("Verificando cuántas cuotas se van a limpiar...")
    
    query_verificar = text("""
        SELECT 
            COUNT(*) AS total_cuotas_a_limpiar,
            SUM(total_pagado) AS monto_total_a_limpiar
        FROM cuotas
        WHERE total_pagado > 0 OR fecha_pago IS NOT NULL
    """)
    
    resultado = db.execute(query_verificar).fetchone()
    if resultado:
        total_cuotas = resultado[0] or 0
        monto_total = resultado[1] or Decimal("0.00")
        
        print(f"  Cuotas a limpiar: {total_cuotas}")
        print(f"  Monto total a limpiar: ${monto_total:,.2f}")
        
        return total_cuotas, monto_total
    
    return 0, Decimal("0.00")


def limpiar_total_pagado(db):
    """Limpia total_pagado en todas las cuotas"""
    print("Limpiando total_pagado en todas las cuotas...")
    
    try:
        query_limpiar = text("""
            UPDATE cuotas
            SET 
                total_pagado = 0.00,
                fecha_pago = NULL,
                estado = CASE 
                    WHEN fecha_vencimiento < CURRENT_DATE THEN 'ATRASADO'
                    ELSE 'PENDIENTE'
                END,
                dias_mora = CASE 
                    WHEN fecha_vencimiento < CURRENT_DATE THEN 
                        EXTRACT(DAY FROM (CURRENT_DATE - fecha_vencimiento))::INTEGER
                    ELSE 0
                END,
                dias_morosidad = CASE 
                    WHEN fecha_vencimiento < CURRENT_DATE THEN 
                        EXTRACT(DAY FROM (CURRENT_DATE - fecha_vencimiento))::INTEGER
                    ELSE 0
                END,
                actualizado_en = NOW()
            WHERE total_pagado > 0 OR fecha_pago IS NOT NULL
        """)
        
        resultado = db.execute(query_limpiar)
        db.commit()
        
        filas_afectadas = resultado.rowcount
        print(f"  Cuotas actualizadas: {filas_afectadas}")
        
        return filas_afectadas
        
    except Exception as e:
        print(f"  [ERROR] Error limpiando total_pagado: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 0


def verificar_despues_de_limpiar(db):
    """Verifica el estado después de limpiar"""
    print("Verificando estado después de limpiar...")
    
    query_verificar = text("""
        SELECT 
            COUNT(*) AS total_cuotas,
            COUNT(CASE WHEN total_pagado = 0 OR total_pagado IS NULL THEN 1 END) AS cuotas_con_total_pagado_cero,
            COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_total_pagado_mayor_cero,
            COUNT(CASE WHEN fecha_pago IS NULL THEN 1 END) AS cuotas_sin_fecha_pago
        FROM cuotas
    """)
    
    resultado = db.execute(query_verificar).fetchone()
    if resultado:
        total_cuotas = resultado[0]
        cuotas_cero = resultado[1]
        cuotas_con_pagos = resultado[2]
        cuotas_sin_fecha = resultado[3]
        
        print(f"  Total cuotas: {total_cuotas}")
        print(f"  Cuotas con total_pagado = 0: {cuotas_cero}")
        print(f"  Cuotas con total_pagado > 0: {cuotas_con_pagos}")
        print(f"  Cuotas sin fecha_pago: {cuotas_sin_fecha}")
        
        if cuotas_con_pagos == 0:
            print()
            print("  [OK] Limpieza completada exitosamente")
            print("     Todas las cuotas tienen total_pagado = 0")
        else:
            print()
            print(f"  [ADVERTENCIA] Aun hay {cuotas_con_pagos} cuotas con total_pagado > 0")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Limpiar total_pagado en tabla cuotas')
    parser.add_argument('--yes', action='store_true', help='Ejecutar sin confirmación')
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("LIMPIEZA: Columna total_pagado en tabla cuotas")
        print("=" * 70)
        print()
        
        # Verificar antes de limpiar
        total_cuotas, monto_total = verificar_antes_de_limpiar(db)
        
        if total_cuotas == 0:
            print()
            print("[INFO] No hay cuotas que limpiar")
            print("  Todas las cuotas ya tienen total_pagado = 0")
            return
        
        print()
        print("=" * 70)
        print("ADVERTENCIA")
        print("=" * 70)
        print(f"Este proceso va a:")
        print(f"  - Limpiar total_pagado en {total_cuotas} cuotas")
        print(f"  - Eliminar ${monto_total:,.2f} en pagos registrados")
        print(f"  - Limpiar fecha_pago en todas las cuotas afectadas")
        print(f"  - Actualizar el estado de las cuotas")
        print()
        print("Se creará un backup antes de limpiar.")
        print("=" * 70)
        print()
        
        if not args.yes:
            respuesta = input("¿Estás seguro de que quieres continuar? (escribe 'SI' para confirmar): ")
            if respuesta.upper() != 'SI':
                print("Operación cancelada por el usuario")
                return
        
        # Crear backup
        print()
        if not crear_backup(db):
            print("[ERROR] No se pudo crear el backup. Operación cancelada.")
            return
        
        # Limpiar
        print()
        filas_afectadas = limpiar_total_pagado(db)
        
        if filas_afectadas > 0:
            print()
            print(f"[OK] Limpieza completada: {filas_afectadas} cuotas actualizadas")
            
            # Verificar después
            print()
            verificar_despues_de_limpiar(db)
            
            print()
            print("=" * 70)
            print("RESUMEN")
            print("=" * 70)
            print("  Backup creado en: cuotas_backup_total_pagado")
            print(f"  Cuotas limpiadas: {filas_afectadas}")
            print("  Estado: total_pagado = 0.00 en todas las cuotas")
            print("=" * 70)
        else:
            print()
            print("[INFO] No se actualizaron cuotas (ya estaban limpias o hubo un error)")
        
    except Exception as e:
        print(f"\n[ERROR] Error en limpieza: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
