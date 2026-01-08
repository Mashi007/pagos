"""Investigar caso específico de cliente INACTIVO con préstamo aprobado"""
import sys
import io
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 70)
print("INVESTIGACION: CLIENTE INACTIVO CON PRESTAMO APROBADO")
print("=" * 70)

# Obtener información completa del cliente
resultado = db.execute(
    text("""
        SELECT 
            c.id,
            c.cedula,
            c.nombres,
            c.estado,
            c.activo,
            c.fecha_registro,
            c.fecha_actualizacion,
            c.telefono,
            c.email
        FROM clientes c
        WHERE c.estado = 'INACTIVO'
        AND EXISTS (
            SELECT 1 FROM prestamos p 
            WHERE p.cedula = c.cedula AND p.estado = 'APROBADO'
        )
    """)
)

cliente = resultado.fetchone()

if cliente:
    cliente_id, cedula, nombres, estado, activo, fecha_reg, fecha_act, telefono, email = cliente
    print(f"\nCLIENTE ENCONTRADO:")
    print(f"  ID: {cliente_id}")
    print(f"  Cedula: {cedula}")
    print(f"  Nombres: {nombres}")
    print(f"  Estado: {estado}")
    print(f"  Activo: {activo}")
    print(f"  Fecha registro: {fecha_reg}")
    print(f"  Fecha actualizacion: {fecha_act}")
    print(f"  Telefono: {telefono}")
    print(f"  Email: {email}")

    # Obtener información del préstamo
    print("\n" + "-" * 70)
    print("PRESTAMO APROBADO ASOCIADO:")
    print("-" * 70)
    
    resultado = db.execute(
        text("""
            SELECT 
                p.id,
                p.estado,
                p.total_financiamiento,
                p.numero_cuotas,
                p.cuota_periodo,
                p.fecha_aprobacion,
                p.fecha_registro,
                COUNT(cu.id) as total_cuotas,
                COALESCE(SUM(cu.total_pagado), 0) as total_pagado_cuotas
            FROM prestamos p
            LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
            WHERE p.cedula = :cedula
            AND p.estado = 'APROBADO'
            GROUP BY p.id, p.estado, p.total_financiamiento, p.numero_cuotas, 
                     p.cuota_periodo, p.fecha_aprobacion, p.fecha_registro
        """),
        {"cedula": cedula}
    )
    
    prestamo = resultado.fetchone()
    if prestamo:
        prestamo_id, prestamo_estado, total_fin, num_cuotas, cuota_per, fecha_aprob, fecha_reg_prestamo, total_cuotas, total_pagado = prestamo
        print(f"  Prestamo ID: {prestamo_id}")
        print(f"  Estado: {prestamo_estado}")
        print(f"  Total financiamiento: ${total_fin:,.2f}")
        print(f"  Numero cuotas: {num_cuotas}")
        print(f"  Cuota periodo: ${cuota_per:,.2f}")
        print(f"  Fecha aprobacion: {fecha_aprob}")
        print(f"  Fecha registro: {fecha_reg_prestamo}")
        print(f"  Total cuotas generadas: {total_cuotas}")
        print(f"  Total pagado en cuotas: ${total_pagado:,.2f}")

    # Verificar pagos
    print("\n" + "-" * 70)
    print("PAGOS REGISTRADOS:")
    print("-" * 70)
    
    resultado = db.execute(
        text("""
            SELECT 
                COUNT(*) as total_pagos,
                SUM(monto_pagado) as total_pagado,
                MIN(fecha_pago) as primer_pago,
                MAX(fecha_pago) as ultimo_pago
            FROM pagos
            WHERE cedula = :cedula
            AND activo = TRUE
        """),
        {"cedula": cedula}
    )
    
    pagos_info = resultado.fetchone()
    if pagos_info:
        total_pagos, total_pagado_pagos, primer_pago, ultimo_pago = pagos_info
        print(f"  Total pagos activos: {total_pagos or 0}")
        print(f"  Total pagado: ${total_pagado_pagos or 0:,.2f}")
        print(f"  Primer pago: {primer_pago}")
        print(f"  Ultimo pago: {ultimo_pago}")

    # Análisis temporal
    print("\n" + "-" * 70)
    print("ANALISIS TEMPORAL:")
    print("-" * 70)
    
    if fecha_aprob and fecha_act:
        if fecha_act < fecha_aprob:
            print(f"  [PROBLEMA] Cliente se inactivo ANTES de la aprobacion")
            print(f"    Fecha actualizacion cliente: {fecha_act}")
            print(f"    Fecha aprobacion prestamo: {fecha_aprob}")
            print(f"    Diferencia: {(fecha_aprob - fecha_act).days} dias")
        else:
            print(f"  Cliente se inactivo DESPUES de la aprobacion")
            print(f"    Fecha aprobacion prestamo: {fecha_aprob}")
            print(f"    Fecha actualizacion cliente: {fecha_act}")
            print(f"    Diferencia: {(fecha_act - fecha_aprob).days} dias")

    # Recomendación
    print("\n" + "=" * 70)
    print("RECOMENDACION:")
    print("=" * 70)
    
    if total_cuotas and total_pagado and total_pagado > 0:
        print("\n[ACCION] Este cliente deberia estar en estado 'FINALIZADO' en lugar de 'INACTIVO'")
        print("  Razones:")
        print(f"  - Tiene prestamo aprobado con {total_cuotas} cuotas generadas")
        print(f"  - Tiene pagos registrados: ${total_pagado:,.2f}")
        print("  - Ha completado su ciclo de prestamo")
    else:
        print("\n[ACCION] Revisar si este prestamo deberia estar aprobado")
        print("  O si el cliente deberia estar en otro estado")

print("\n" + "=" * 70)

db.close()
