"""Investigar cuotas huérfanas (sin préstamo válido)"""
import sys
import io
from pathlib import Path
from datetime import datetime

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
print("INVESTIGACION: CUOTAS HUERFANAS")
print("=" * 70)

# 1. Resumen general
print("\n1. RESUMEN GENERAL:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_cuotas_huerfanas,
        COUNT(DISTINCT prestamo_id) AS prestamos_inexistentes,
        MIN(prestamo_id) AS prestamo_id_minimo,
        MAX(prestamo_id) AS prestamo_id_maximo,
        SUM(total_pagado) AS total_pagado_huerfanas,
        COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_pagos
    FROM cuotas c
    LEFT JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.id IS NULL
"""))

row = resultado.fetchone()
total, prestamos_inexistentes, min_id, max_id, total_pagado, cuotas_con_pagos = row

print(f"Total cuotas huérfanas: {total:,}")
print(f"Prestamos inexistentes referenciados: {prestamos_inexistentes:,}")
print(f"Rango de prestamo_id: {min_id} - {max_id}")
print(f"Total pagado en cuotas huérfanas: ${total_pagado:,.2f}" if total_pagado else "Total pagado: $0.00")
print(f"Cuotas huérfanas con pagos: {cuotas_con_pagos:,}")

# 2. Distribución por prestamo_id
print("\n2. DISTRIBUCION POR PRESTAMO_ID:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        prestamo_id,
        COUNT(*) AS total_cuotas,
        SUM(total_pagado) AS total_pagado,
        COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_pagadas,
        MIN(numero_cuota) AS primera_cuota,
        MAX(numero_cuota) AS ultima_cuota
    FROM cuotas c
    LEFT JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.id IS NULL
    GROUP BY prestamo_id
    ORDER BY prestamo_id
    LIMIT 20
"""))

print("\nPrimeros 20 prestamo_id inexistentes:")
print(f"{'Prestamo ID':<12} {'Cuotas':<8} {'Total Pagado':<15} {'Cuotas Pagadas':<15} {'Rango Cuotas':<15}")
print("-" * 70)

for row in resultado.fetchall():
    prestamo_id, total_cuotas, total_pagado, cuotas_pagadas, primera, ultima = row
    rango = f"{primera}-{ultima}" if primera != ultima else str(primera)
    print(f"{prestamo_id:<12} {total_cuotas:<8} ${total_pagado:>13,.2f} {cuotas_pagadas:<15} {rango:<15}")

# 3. Cuotas huérfanas con pagos
print("\n3. CUOTAS HUERFANAS CON PAGOS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_cuotas_con_pagos,
        SUM(total_pagado) AS total_pagado,
        COUNT(DISTINCT prestamo_id) AS prestamos_afectados
    FROM cuotas c
    LEFT JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.id IS NULL AND c.total_pagado > 0
"""))

row = resultado.fetchone()
total_con_pagos, total_pagado, prestamos_afectados = row

print(f"Cuotas huérfanas con pagos: {total_con_pagos:,}")
print(f"Total pagado: ${total_pagado:,.2f}" if total_pagado else "Total pagado: $0.00")
print(f"Prestamos inexistentes afectados: {prestamos_afectados:,}")

if total_con_pagos > 0:
    print("\n⚠️ ADVERTENCIA: Hay cuotas huérfanas con pagos registrados")
    print("   Estas cuotas tienen dinero pagado pero no tienen préstamo asociado")

# 4. Verificar si hay pagos registrados en tabla pagos para estos prestamo_id
print("\n4. VERIFICAR PAGOS EN TABLA PAGOS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_pagos,
        COUNT(DISTINCT prestamo_id) AS prestamos_con_pagos,
        SUM(monto_pagado) AS total_monto_pagado
    FROM pagos
    WHERE prestamo_id IN (
        SELECT DISTINCT c.prestamo_id
        FROM cuotas c
        LEFT JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.id IS NULL
    )
"""))

row = resultado.fetchone()
total_pagos, prestamos_con_pagos, total_monto = row

print(f"Pagos registrados para prestamos inexistentes: {total_pagos:,}")
print(f"Prestamos inexistentes con pagos: {prestamos_con_pagos:,}")
print(f"Total monto en pagos: ${total_monto:,.2f}" if total_monto else "Total monto: $0.00")

# 5. Verificar relación con tabla pago_cuotas (si existe)
print("\n5. VERIFICAR RELACION CON TABLA PAGO_CUOTAS:")
print("-" * 70)

try:
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total_relaciones_pago_cuota
        FROM pago_cuotas pc
        INNER JOIN cuotas c ON pc.cuota_id = c.id
        LEFT JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.id IS NULL
    """))
    total_relaciones = resultado.scalar()
    print(f"Relaciones pago_cuotas con cuotas huérfanas: {total_relaciones:,}")
except Exception as e:
    db.rollback()
    print(f"Tabla pago_cuotas no existe o no accesible: {type(e).__name__}")
    print("  (Esto es normal si la tabla aún no ha sido creada)")

# 6. Ejemplos de cuotas huérfanas
print("\n6. EJEMPLOS DE CUOTAS HUERFANAS:")
print("-" * 70)

try:
    resultado = db.execute(text("""
        SELECT 
            c.id AS cuota_id,
            c.prestamo_id,
            c.numero_cuota,
            c.fecha_vencimiento,
            c.monto_cuota,
            c.total_pagado,
            c.estado
        FROM cuotas c
        LEFT JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.id IS NULL
        ORDER BY c.prestamo_id, c.numero_cuota
        LIMIT 10
    """))

    print("\nPrimeras 10 cuotas huérfanas:")
    print(f"{'Cuota ID':<10} {'Prestamo ID':<12} {'Num':<5} {'Vencimiento':<12} {'Monto':<12} {'Pagado':<12} {'Estado':<12}")
    print("-" * 80)

    for row in resultado.fetchall():
        cuota_id, prestamo_id, numero, vencimiento, monto, pagado, estado = row
        venc_str = str(vencimiento) if vencimiento else "N/A"
        print(f"{cuota_id:<10} {prestamo_id:<12} {numero:<5} {venc_str:<12} ${monto:>10,.2f} ${pagado:>10,.2f} {estado:<12}")
except Exception as e:
    db.rollback()
    print(f"Error al obtener ejemplos: {type(e).__name__}")
    print("  Continuando con el análisis...")

# 7. Análisis de fechas
print("\n7. ANALISIS DE FECHAS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        MIN(fecha_vencimiento) AS fecha_minima,
        MAX(fecha_vencimiento) AS fecha_maxima
    FROM cuotas c
    LEFT JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.id IS NULL
"""))

row = resultado.fetchone()
fecha_min, fecha_max = row

print(f"Fecha de vencimiento más antigua: {fecha_min}")
print(f"Fecha de vencimiento más reciente: {fecha_max}")

# 8. Recomendaciones
print("\n8. RECOMENDACIONES:")
print("-" * 70)

if total_con_pagos > 0:
    print("⚠️ CRITICO: Hay cuotas huérfanas con pagos registrados")
    print("   - NO eliminar estas cuotas sin investigar más")
    print("   - Pueden ser datos históricos importantes")
    print("   - Verificar si los préstamos fueron eliminados por error")
else:
    print("✅ Las cuotas huérfanas NO tienen pagos registrados")
    print("   - Pueden ser eliminadas de forma segura")
    print("   - Son probablemente datos de préstamos eliminados o migrados")

print(f"\nTotal cuotas huérfanas a revisar: {total:,}")
print(f"Prestamos inexistentes referenciados: {prestamos_inexistentes:,}")

print("\n" + "=" * 70)

db.close()
