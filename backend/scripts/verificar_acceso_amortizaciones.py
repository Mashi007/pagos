"""
Script para verificar acceso a amortizaciones de todos los préstamos
"""

import os
import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.prestamo import Prestamo
from app.models.amortizacion import Cuota
from sqlalchemy import func, desc

def verificar_amortizaciones():
    """Verifica acceso a todas las amortizaciones"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("VERIFICACIÓN DE ACCESO A AMORTIZACIONES")
        print("=" * 80)
        print(f"\n📊 Base de datos: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'N/A'}")
        print()
        
        # 1. Contar total de préstamos
        total_prestamos = db.query(Prestamo).count()
        print(f"✅ Total de préstamos en BD: {total_prestamos}")
        
        # 2. Contar total de cuotas/amortizaciones
        total_cuotas = db.query(Cuota).count()
        print(f"✅ Total de cuotas/amortizaciones en BD: {total_cuotas}")
        
        # 3. Préstamos con cuotas
        prestamos_con_cuotas = (
            db.query(Prestamo.id)
            .join(Cuota, Prestamo.id == Cuota.prestamo_id)
            .distinct()
            .count()
        )
        print(f"✅ Préstamos con cuotas generadas: {prestamos_con_cuotas}")
        
        # 4. Préstamos sin cuotas
        prestamos_sin_cuotas = total_prestamos - prestamos_con_cuotas
        print(f"⚠️  Préstamos sin cuotas: {prestamos_sin_cuotas}")
        
        # 5. Estadísticas por estado de préstamo
        print("\n" + "-" * 80)
        print("ESTADÍSTICAS POR ESTADO DE PRÉSTAMO")
        print("-" * 80)
        
        prestamos_por_estado = (
            db.query(Prestamo.estado, func.count(Prestamo.id))
            .group_by(Prestamo.estado)
            .all()
        )
        
        for estado, count in prestamos_por_estado:
            cuotas_estado = (
                db.query(func.count(Cuota.id))
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(Prestamo.estado == estado)
                .scalar() or 0
            )
            print(f"  {estado:15s}: {count:4d} préstamos, {cuotas_estado:6d} cuotas")
        
        # 6. Estadísticas por estado de cuotas
        print("\n" + "-" * 80)
        print("ESTADÍSTICAS POR ESTADO DE CUOTAS")
        print("-" * 80)
        
        cuotas_por_estado = (
            db.query(Cuota.estado, func.count(Cuota.id))
            .group_by(Cuota.estado)
            .all()
        )
        
        for estado, count in cuotas_por_estado:
            porcentaje = (count / total_cuotas * 100) if total_cuotas > 0 else 0
            print(f"  {estado:15s}: {count:6d} cuotas ({porcentaje:5.1f}%)")
        
        # 7. Detalle de préstamos aprobados con sus cuotas
        print("\n" + "-" * 80)
        print("DETALLE DE PRÉSTAMOS APROBADOS CON CUOTAS (Primeros 10)")
        print("-" * 80)
        
        prestamos_aprobados = (
            db.query(Prestamo)
            .filter(Prestamo.estado == "APROBADO")
            .join(Cuota, Prestamo.id == Cuota.prestamo_id)
            .distinct()
            .order_by(desc(Prestamo.fecha_registro))
            .limit(10)
            .all()
        )
        
        for prestamo in prestamos_aprobados:
            cuotas_prestamo = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).all()
            
            total_cuotas_p = len(cuotas_prestamo)
            cuotas_pagadas = len([c for c in cuotas_prestamo if c.estado == "PAGADO"])
            cuotas_pendientes = len([c for c in cuotas_prestamo if c.estado == "PENDIENTE"])
            cuotas_vencidas = len([c for c in cuotas_prestamo if c.esta_vencida])
            
            saldo_total = sum(
                c.capital_pendiente + c.interes_pendiente + c.monto_mora
                for c in cuotas_prestamo
            )
            
            print(f"\n  📋 Préstamo ID: {prestamo.id}")
            print(f"     Cliente: {prestamo.nombres} (Cédula: {prestamo.cedula})")
            print(f"     Monto: ${prestamo.total_financiamiento:,.2f}")
            print(f"     Cuotas: {total_cuotas_p} total | {cuotas_pagadas} pagadas | {cuotas_pendientes} pendientes | {cuotas_vencidas} vencidas")
            print(f"     Saldo pendiente: ${saldo_total:,.2f}")
        
        # 8. Resumen de montos
        print("\n" + "-" * 80)
        print("RESUMEN DE MONTOS")
        print("-" * 80)
        
        total_financiamiento = (
            db.query(func.sum(Prestamo.total_financiamiento))
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or Decimal("0")
        )
        
        total_capital_pendiente = (
            db.query(func.sum(Cuota.capital_pendiente))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or Decimal("0")
        )
        
        total_interes_pendiente = (
            db.query(func.sum(Cuota.interes_pendiente))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or Decimal("0")
        )
        
        total_mora = (
            db.query(func.sum(Cuota.monto_mora))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or Decimal("0")
        )
        
        total_pagado = (
            db.query(func.sum(Cuota.total_pagado))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar() or Decimal("0")
        )
        
        print(f"  Total financiamiento (APROBADOS): ${float(total_financiamiento):,.2f}")
        print(f"  Total pagado: ${float(total_pagado):,.2f}")
        print(f"  Capital pendiente: ${float(total_capital_pendiente):,.2f}")
        print(f"  Interés pendiente: ${float(total_interes_pendiente):,.2f}")
        print(f"  Mora acumulada: ${float(total_mora):,.2f}")
        print(f"  Total pendiente: ${float(total_capital_pendiente + total_interes_pendiente + total_mora):,.2f}")
        
        # 9. Verificación de acceso completo
        print("\n" + "=" * 80)
        print("✅ VERIFICACIÓN COMPLETA")
        print("=" * 80)
        print(f"✅ Acceso a tabla 'prestamos': OK ({total_prestamos} registros)")
        print(f"✅ Acceso a tabla 'cuotas': OK ({total_cuotas} registros)")
        print(f"✅ Relación prestamos-cuotas: OK ({prestamos_con_cuotas} préstamos con cuotas)")
        print(f"✅ Cálculos y agregaciones: OK")
        print("\n🎉 ACCESO COMPLETO A AMORTIZACIONES CONFIRMADO")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR al acceder a las amortizaciones:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    verificar_amortizaciones()

