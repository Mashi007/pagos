"""Script para corregir cliente INACTIVO con préstamo aprobado"""
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
print("CORRECCION: CLIENTE INACTIVO CON PRESTAMO APROBADO")
print("=" * 70)
print("\nCaso: Cliente ID 25728 (V20428105) - PEDRO JAVIER ALDANA RAMIREZ")
print("Problema: Cliente en estado INACTIVO con prestamo APROBADO")
print("\n" + "=" * 70)

# Verificar estado actual
print("\n1. ESTADO ACTUAL DEL CLIENTE:")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            c.id,
            c.cedula,
            c.nombres,
            c.estado,
            c.activo,
            c.fecha_actualizacion,
            COUNT(p.id) AS prestamos_aprobados
        FROM clientes c
        LEFT JOIN prestamos p ON c.cedula = p.cedula AND p.estado = 'APROBADO'
        WHERE c.id = 25728
        GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo, c.fecha_actualizacion
    """)
)

cliente_actual = resultado.fetchone()
if cliente_actual:
    cliente_id, cedula, nombres, estado, activo, fecha_act, prestamos = cliente_actual
    print(f"  Cliente ID: {cliente_id}")
    print(f"  Cedula: {cedula}")
    print(f"  Nombres: {nombres}")
    print(f"  Estado actual: {estado}")
    print(f"  Activo: {activo}")
    print(f"  Prestamos aprobados: {prestamos}")

# Verificar préstamo
print("\n2. ESTADO ACTUAL DEL PRESTAMO:")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            p.id,
            p.cedula,
            p.estado,
            p.total_financiamiento,
            p.fecha_aprobacion,
            COUNT(cu.id) AS total_cuotas,
            COALESCE(SUM(cu.total_pagado), 0) AS total_pagado
        FROM prestamos p
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.id = 7267
        GROUP BY p.id, p.cedula, p.estado, p.total_financiamiento, p.fecha_aprobacion
    """)
)

prestamo_actual = resultado.fetchone()
if prestamo_actual:
    prestamo_id, prestamo_cedula, prestamo_estado, total_fin, fecha_aprob, total_cuotas, total_pagado = prestamo_actual
    print(f"  Prestamo ID: {prestamo_id}")
    print(f"  Estado: {prestamo_estado}")
    print(f"  Total financiamiento: ${total_fin:,.2f}")
    print(f"  Fecha aprobacion: {fecha_aprob}")
    print(f"  Total cuotas: {total_cuotas}")
    print(f"  Total pagado: ${total_pagado:,.2f}")

# Mostrar opciones
print("\n" + "=" * 70)
print("3. OPCIONES DE CORRECCION:")
print("=" * 70)
print("\nOPCION 1: Cambiar estado del cliente a 'FINALIZADO'")
print("  - Usar si el prestamo es valido")
print("  - El cliente completo su ciclo (aunque no haya pagos)")
print("\nOPCION 2: Cambiar estado del prestamo a 'CANCELADO'")
print("  - Usar si el prestamo no deberia estar aprobado")
print("  - El cliente es realmente pasivo")

# Solicitar confirmación
print("\n" + "=" * 70)
print("4. CONFIRMACION REQUERIDA:")
print("=" * 70)
print("\nIMPORTANTE: Este script requiere confirmacion manual")
print("Por favor, ejecuta la correccion manualmente usando el script SQL:")
print("  scripts/sql/corregir_cliente_inactivo_prestamo.sql")
print("\nO descomenta y ejecuta la opcion deseada en este script Python")

# OPCION 1: Cambiar cliente a FINALIZADO
# DESCOMENTAR PARA EJECUTAR:
# print("\nEjecutando OPCION 1: Cambiar cliente a FINALIZADO...")
# db.execute(
#     text("""
#         UPDATE clientes 
#         SET estado = 'FINALIZADO',
#             activo = FALSE,
#             fecha_actualizacion = CURRENT_TIMESTAMP
#         WHERE id = 25728
#           AND estado = 'INACTIVO'
#     """)
# )
# db.commit()
# print("Cliente actualizado a FINALIZADO")

# OPCION 2: Cambiar préstamo a CANCELADO
# DESCOMENTAR PARA EJECUTAR:
# print("\nEjecutando OPCION 2: Cambiar prestamo a CANCELADO...")
# db.execute(
#     text("""
#         UPDATE prestamos 
#         SET estado = 'CANCELADO',
#             fecha_actualizacion = CURRENT_TIMESTAMP
#         WHERE id = 7267
#           AND estado = 'APROBADO'
#           AND cedula = 'V20428105'
#     """)
# )
# db.commit()
# print("Prestamo actualizado a CANCELADO")

# Verificación final
print("\n" + "=" * 70)
print("5. VERIFICACION FINAL:")
print("=" * 70)

resultado = db.execute(
    text("""
        SELECT COUNT(*) 
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.estado = 'INACTIVO'
          AND p.estado = 'APROBADO'
    """)
)

casos_restantes = resultado.scalar()
print(f"\nClientes INACTIVOS con prestamos aprobados: {casos_restantes}")

if casos_restantes == 0:
    print("\n[OK] La regla de negocio se cumple correctamente")
else:
    print(f"\n[ATENCION] Aun quedan {casos_restantes} casos por corregir")

print("\n" + "=" * 70)

db.close()
