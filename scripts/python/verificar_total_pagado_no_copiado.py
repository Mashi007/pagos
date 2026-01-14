#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que NO hay datos copiados en cuota.total_pagado

Este script confirma que la columna total_pagado está VACIA
antes de aplicar los pagos conciliados.

Uso:
    python scripts/python/verificar_total_pagado_no_copiado.py
"""

import sys
from pathlib import Path
from decimal import Decimal

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db.session import SessionLocal


def verificar_no_copiado():
    """Verifica que NO hay datos copiados en total_pagado"""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("VERIFICACION: NO hay datos copiados en cuota.total_pagado")
        print("=" * 70)
        print()
        
        # Verificación principal
        query = text("""
            SELECT 
                COUNT(*) AS total_cuotas,
                COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_datos,
                COUNT(CASE WHEN total_pagado = 0 OR total_pagado IS NULL THEN 1 END) AS cuotas_vacias,
                SUM(CASE WHEN total_pagado > 0 THEN total_pagado ELSE 0 END) AS monto_total_copiado
            FROM cuotas
        """)
        
        resultado = db.execute(query).fetchone()
        
        if resultado:
            total_cuotas = resultado[0]
            cuotas_con_datos = resultado[1]
            cuotas_vacias = resultado[2]
            monto_total = resultado[3] or Decimal("0.00")
            
            print("[VERIFICACION PRINCIPAL]")
            print("-" * 70)
            print(f"  Total cuotas: {total_cuotas}")
            print(f"  Cuotas con total_pagado > 0: {cuotas_con_datos}")
            print(f"  Cuotas con total_pagado = 0 o NULL: {cuotas_vacias}")
            print(f"  Monto total copiado: ${monto_total:,.2f}")
            print()
            
            if cuotas_con_datos == 0:
                print("  [OK] CONFIRMADO: NO hay datos copiados en cuota.total_pagado")
                print("     - Todas las cuotas tienen total_pagado = 0.00")
                print("     - La columna esta completamente vacia")
                print("     - Lista para recibir los pagos conciliados")
            else:
                print("  [ADVERTENCIA] HAY datos copiados en cuota.total_pagado")
                print(f"     - {cuotas_con_datos} cuotas tienen datos")
                print(f"     - Monto total: ${monto_total:,.2f}")
                print("     - Necesitas limpiar antes de aplicar pagos")
        
        print()
        
        # Verificación adicional: fecha_pago
        query_fecha = text("""
            SELECT 
                COUNT(CASE WHEN fecha_pago IS NOT NULL THEN 1 END) AS cuotas_con_fecha_pago,
                COUNT(CASE WHEN fecha_pago IS NOT NULL AND total_pagado > 0 THEN 1 END) AS cuotas_con_fecha_y_pago
            FROM cuotas
        """)
        
        resultado_fecha = db.execute(query_fecha).fetchone()
        if resultado_fecha:
            cuotas_con_fecha = resultado_fecha[0]
            cuotas_con_fecha_y_pago = resultado_fecha[1]
            
            print("[VERIFICACION ADICIONAL: fecha_pago]")
            print("-" * 70)
            print(f"  Cuotas con fecha_pago: {cuotas_con_fecha}")
            print(f"  Cuotas con fecha_pago Y total_pagado > 0: {cuotas_con_fecha_y_pago}")
            print()
        
        # Verificación adicional: estado
        query_estado = text("""
            SELECT 
                estado,
                COUNT(*) AS cantidad,
                COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS con_datos
            FROM cuotas
            GROUP BY estado
            ORDER BY cantidad DESC
        """)
        
        resultados_estado = db.execute(query_estado).fetchall()
        
        print("[VERIFICACION ADICIONAL: estado]")
        print("-" * 70)
        for row in resultados_estado:
            estado = row[0]
            cantidad = row[1]
            con_datos = row[2]
            print(f"  {estado}: {cantidad} cuotas (con datos: {con_datos})")
        
        print()
        print("=" * 70)
        print("RESUMEN FINAL")
        print("=" * 70)
        
        if cuotas_con_datos == 0:
            print("[CONFIRMADO] NO hay datos copiados en cuota.total_pagado")
            print("  - Todas las cuotas tienen total_pagado = 0.00")
            print("  - La columna esta completamente vacia")
            print("  - Puedes proceder a aplicar los pagos conciliados")
        else:
            print("[ADVERTENCIA] HAY datos copiados en cuota.total_pagado")
            print(f"  - {cuotas_con_datos} cuotas tienen datos")
            print(f"  - Monto total: ${monto_total:,.2f}")
            print("  - Ejecuta: python scripts/python/vaciar_total_pagado_cuotas.py")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Error en verificación: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    verificar_no_copiado()
