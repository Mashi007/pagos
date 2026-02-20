"""
Script de auditoría integral: Verifica pagos conciliados para un préstamo específico.
Compara estado esperado vs. estado actual en la BD.

Uso: python auditoria_pagos_conciliados.py <prestamo_id>
Ejemplo: python auditoria_pagos_conciliados.py 4601
"""

import sys
from datetime import datetime, timedelta
from decimal import Decimal

# Importar modelos y configuración
sys.path.insert(0, '/app')
from app.core.database import SessionLocal
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.pago import Pago

def auditoria_prestamo(prestamo_id: int):
    """Realiza auditoría completa de un préstamo."""
    db = SessionLocal()
    
    try:
        # 1. Obtener préstamo
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            print(f"❌ Préstamo {prestamo_id} no encontrado")
            return
        
        print(f"\n{'='*80}")
        print(f"AUDITORIA INTEGRAL - PRESTAMO #{prestamo_id}")
        print(f"{'='*80}")
        print(f"Cliente: {prestamo.nombres} (Cédula: {prestamo.cedula})")
        print(f"Total Financiamiento: ${float(prestamo.total_financiamiento):.2f}")
        print(f"Estado: {prestamo.estado}")
        print(f"Número de Cuotas: {prestamo.numero_cuotas}")
        print(f"{'='*80}\n")
        
        # 2. Obtener todas las cuotas
        cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota).all()
        print(f"✓ CUOTAS ENCONTRADAS: {len(cuotas)}")
        print(f"{'-'*80}")
        
        if not cuotas:
            print("⚠️  No hay cuotas generadas para este préstamo")
            return
        
        # 3. Analizar cada cuota
        for idx, cuota in enumerate(cuotas, 1):
            print(f"\n📋 CUOTA #{cuota.numero_cuota}")
            print(f"   Fecha Vencimiento: {cuota.fecha_vencimiento}")
            print(f"   Monto: ${float(cuota.monto):.2f}")
            print(f"   Estado BD: {cuota.estado}")
            print(f"   Total Pagado (cuota.total_pagado): ${float(cuota.total_pagado or 0):.2f}")
            
            # 4. Buscar pagos vinculados directamente (pago_id)
            if cuota.pago_id:
                pago_directo = db.query(Pago).filter(Pago.id == cuota.pago_id).first()
                if pago_directo:
                    print(f"   ✅ PAGO DIRECTO ENCONTRADO (pago_id={cuota.pago_id})")
                    print(f"      - Monto: ${float(pago_directo.monto_pagado):.2f}")
                    print(f"      - Conciliado: {pago_directo.conciliado}")
                    print(f"      - Verificado Concordancia: {pago_directo.verificado_concordancia}")
                    print(f"      - Fecha: {pago_directo.fecha_pago}")
                else:
                    print(f"   ⚠️  pago_id={cuota.pago_id} NO EXISTE en tabla pagos")
            else:
                print(f"   ℹ️  Sin pago_id directo")
            
            # 5. Buscar pagos por rango de fechas (estrategia alternativa)
            if cuota.fecha_vencimiento:
                fecha_inicio = cuota.fecha_vencimiento - timedelta(days=15)
                fecha_fin = cuota.fecha_vencimiento + timedelta(days=15)
                
                pagos_en_rango = db.query(Pago).filter(
                    Pago.prestamo_id == prestamo_id,
                    Pago.fecha_pago >= datetime.combine(fecha_inicio, datetime.min.time()),
                    Pago.fecha_pago <= datetime.combine(fecha_fin, datetime.max.time()),
                ).all()
                
                if pagos_en_rango:
                    print(f"   🔍 PAGOS ENCONTRADOS EN RANGO [{fecha_inicio} ... {fecha_fin}]: {len(pagos_en_rango)}")
                    for pago in pagos_en_rango:
                        conciliado_text = "✅ CONCILIADO" if pago.conciliado else "❌ NO CONCILIADO"
                        verificado_text = f"(Verificado: {pago.verificado_concordancia})" if pago.verificado_concordancia else ""
                        print(f"      • Pago {pago.id}: ${float(pago.monto_pagado):.2f} - {conciliado_text} {verificado_text}")
                        print(f"        Fecha: {pago.fecha_pago} | Referencia: {pago.referencia_pago}")
                else:
                    print(f"   ❌ NO HAY PAGOS en rango [{fecha_inicio} ... {fecha_fin}]")
        
        # 6. Resumen de pagos del préstamo
        print(f"\n{'-'*80}")
        print(f"RESUMEN DE PAGOS - PRESTAMO #{prestamo_id}")
        print(f"{'-'*80}")
        
        todos_los_pagos = db.query(Pago).filter(Pago.prestamo_id == prestamo_id).order_by(Pago.fecha_pago).all()
        print(f"\nTotal de pagos registrados: {len(todos_los_pagos)}")
        
        pagos_conciliados = [p for p in todos_los_pagos if p.conciliado or p.verificado_concordancia == "SI"]
        print(f"Pagos conciliados: {len(pagos_conciliados)}")
        
        if pagos_conciliados:
            print(f"\n{'='*80}")
            print(f"PAGOS CONCILIADOS DETALLE:")
            print(f"{'='*80}")
            for pago in pagos_conciliados:
                print(f"\n✅ Pago ID: {pago.id}")
                print(f"   Monto: ${float(pago.monto_pagado):.2f}")
                print(f"   Fecha: {pago.fecha_pago}")
                print(f"   Conciliado: {pago.conciliado}")
                print(f"   Verificado Concordancia: {pago.verificado_concordancia}")
                print(f"   Referencia: {pago.referencia_pago}")
                if pago.cuota_id:
                    print(f"   Vinculado a Cuota: {pago.cuota_id}")
        
        total_conciliado = sum(float(p.monto_pagado) for p in pagos_conciliados)
        print(f"\n{'='*80}")
        print(f"TOTALES:")
        print(f"  Total Financiamiento: ${float(prestamo.total_financiamiento):.2f}")
        print(f"  Total Pagos Conciliados: ${total_conciliado:.2f}")
        print(f"  Saldo Pendiente: ${float(prestamo.total_financiamiento) - total_conciliado:.2f}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python auditoria_pagos_conciliados.py <prestamo_id>")
        print("Ejemplo: python auditoria_pagos_conciliados.py 4601")
        sys.exit(1)
    
    try:
        prestamo_id = int(sys.argv[1])
        auditoria_prestamo(prestamo_id)
    except ValueError:
        print(f"Error: {sys.argv[1]} no es un número válido")
        sys.exit(1)
