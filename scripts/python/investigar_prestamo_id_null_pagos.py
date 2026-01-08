"""Investigar por qué todos los pagos tienen prestamo_id = NULL"""
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 80)
print("INVESTIGACION: ¿POR QUÉ TODOS LOS PAGOS TIENEN prestamo_id = NULL?")
print("=" * 80)

# 1. Verificar si los pagos tienen cédula
print("\n1. VERIFICACION DE CEDULA EN PAGOS:")
print("-" * 80)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_pagos,
        COUNT(CASE WHEN cedula IS NOT NULL AND cedula != '' THEN 1 END) AS con_cedula,
        COUNT(CASE WHEN cedula IS NULL OR cedula = '' THEN 1 END) AS sin_cedula,
        COUNT(DISTINCT cedula) AS cedulas_unicas
    FROM pagos
    WHERE activo = TRUE
"""))

row = resultado.fetchone()
total, con_cedula, sin_cedula, cedulas_unicas = row

print(f"Total pagos activos: {total:,}")
print(f"Pagos con cédula: {con_cedula:,}")
print(f"Pagos sin cédula: {sin_cedula:,}")
print(f"Cédulas únicas: {cedulas_unicas:,}")

# 2. Verificar si hay préstamos aprobados para las cédulas de los pagos
print("\n2. VERIFICACION DE PRESTAMOS APROBADOS PARA CEDULAS DE PAGOS:")
print("-" * 80)

resultado = db.execute(text("""
    WITH pagos_con_cedula AS (
        SELECT DISTINCT cedula
        FROM pagos
        WHERE activo = TRUE 
          AND cedula IS NOT NULL 
          AND cedula != ''
    ),
    prestamos_aprobados AS (
        SELECT DISTINCT cedula
        FROM prestamos
        WHERE estado = 'APROBADO'
    )
    SELECT 
        COUNT(DISTINCT p.cedula) AS cedulas_en_pagos,
        COUNT(DISTINCT pr.cedula) AS cedulas_con_prestamos_aprobados,
        COUNT(DISTINCT CASE WHEN pr.cedula IS NOT NULL THEN p.cedula END) AS cedulas_con_match
    FROM pagos_con_cedula p
    LEFT JOIN prestamos_aprobados pr ON p.cedula = pr.cedula
"""))

row = resultado.fetchone()
cedulas_en_pagos, cedulas_con_prestamos, cedulas_con_match = row

print(f"Cédulas únicas en pagos: {cedulas_en_pagos:,}")
print(f"Cédulas con préstamos aprobados: {cedulas_con_prestamos:,}")
print(f"Cédulas que tienen match con préstamos aprobados: {cedulas_con_match:,}")

# 3. Verificar cuántos pagos podrían tener prestamo_id asignado
print("\n3. PAGOS QUE PODRIAN TENER prestamo_id ASIGNADO:")
print("-" * 80)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_pagos,
        COUNT(CASE WHEN p.cedula IS NOT NULL AND p.cedula != '' AND pr.id IS NOT NULL THEN 1 END) AS podrian_tener_prestamo_id,
        COUNT(CASE WHEN p.cedula IS NOT NULL AND p.cedula != '' AND pr.id IS NULL THEN 1 END) AS sin_prestamo_disponible,
        COUNT(CASE WHEN p.cedula IS NULL OR p.cedula = '' THEN 1 END) AS sin_cedula
    FROM pagos p
    LEFT JOIN prestamos pr ON p.cedula = pr.cedula AND pr.estado = 'APROBADO'
    WHERE p.activo = TRUE
"""))

row = resultado.fetchone()
total, podrian_tener, sin_prestamo, sin_cedula = row

print(f"Total pagos activos: {total:,}")
print(f"Pagos que PODRIAN tener prestamo_id (tienen cédula y hay préstamo aprobado): {podrian_tener:,}")
print(f"Pagos con cédula pero SIN préstamo aprobado: {sin_prestamo:,}")
print(f"Pagos sin cédula: {sin_cedula:,}")

# 4. Verificar si hay múltiples préstamos aprobados para la misma cédula
print("\n4. VERIFICACION DE MULTIPLES PRESTAMOS POR CEDULA:")
print("-" * 80)

resultado = db.execute(text("""
    SELECT 
        COUNT(DISTINCT cedula) AS cedulas_con_prestamos,
        COUNT(*) AS total_prestamos_aprobados,
        AVG(prestamos_por_cedula) AS promedio_prestamos_por_cedula,
        MAX(prestamos_por_cedula) AS max_prestamos_por_cedula
    FROM (
        SELECT 
            cedula,
            COUNT(*) AS prestamos_por_cedula
        FROM prestamos
        WHERE estado = 'APROBADO'
        GROUP BY cedula
    ) subq
"""))

row = resultado.fetchone()
cedulas_con_prestamos, total_prestamos, promedio, max_prestamos = row

print(f"Cédulas con préstamos aprobados: {cedulas_con_prestamos:,}")
print(f"Total préstamos aprobados: {total_prestamos:,}")
print(f"Promedio préstamos por cédula: {promedio:.2f}")
print(f"Máximo préstamos por cédula: {max_prestamos}")

# 5. Ejemplos específicos: pagos con cédula pero sin prestamo_id
print("\n5. EJEMPLOS DE PAGOS CON CEDULA PERO SIN prestamo_id:")
print("-" * 80)

resultado = db.execute(text("""
    SELECT 
        p.id AS pago_id,
        p.cedula,
        p.monto_pagado,
        p.fecha_pago,
        p.conciliado,
        p.verificado_concordancia,
        COUNT(pr.id) AS prestamos_aprobados_disponibles,
        STRING_AGG(pr.id::text, ', ') AS ids_prestamos
    FROM pagos p
    LEFT JOIN prestamos pr ON p.cedula = pr.cedula AND pr.estado = 'APROBADO'
    WHERE p.activo = TRUE
      AND p.prestamo_id IS NULL
      AND p.cedula IS NOT NULL
      AND p.cedula != ''
    GROUP BY p.id, p.cedula, p.monto_pagado, p.fecha_pago, p.conciliado, p.verificado_concordancia
    ORDER BY prestamos_aprobados_disponibles DESC, p.fecha_pago DESC
    LIMIT 10
"""))

rows = resultado.fetchall()
if rows:
    print(f"{'Pago ID':<10} {'Cédula':<15} {'Monto':<12} {'Fecha':<12} {'Conciliado':<12} {'Verificado':<12} {'Préstamos Disponibles':<20}")
    print("-" * 80)
    for row in rows:
        pago_id, cedula, monto, fecha, conciliado, verificado, prestamos_disponibles, ids_prestamos = row
        print(f"{pago_id:<10} {cedula:<15} {monto:<12} {fecha or 'N/A':<12} {str(conciliado):<12} {verificado or 'N/A':<12} {prestamos_disponibles:<20}")
        if ids_prestamos:
            print(f"  └─ Préstamos disponibles: {ids_prestamos}")
else:
    print("No se encontraron pagos con cédula pero sin prestamo_id")

# 6. Verificar estructura de la tabla pagos
print("\n6. ESTRUCTURA DE LA TABLA PAGOS:")
print("-" * 80)

resultado = db.execute(text("""
    SELECT 
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_name = 'pagos'
      AND column_name IN ('prestamo_id', 'cedula', 'conciliado', 'verificado_concordancia')
    ORDER BY ordinal_position
"""))

print(f"{'Columna':<30} {'Tipo':<20} {'Nullable':<10} {'Default':<20}")
print("-" * 80)
for row in resultado.fetchall():
    col_name, data_type, is_nullable, col_default = row
    print(f"{col_name:<30} {data_type:<20} {is_nullable:<10} {str(col_default) if col_default else 'NULL':<20}")

# 7. Verificar fechas de pagos
print("\n7. FECHAS DE PAGOS:")
print("-" * 80)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_pagos,
        MIN(fecha_pago) AS fecha_minima,
        MAX(fecha_pago) AS fecha_maxima,
        MIN(fecha_registro) AS fecha_registro_minima,
        MAX(fecha_registro) AS fecha_registro_maxima
    FROM pagos
    WHERE activo = TRUE
"""))

row = resultado.fetchone()
total, fecha_min, fecha_max, fecha_registro_min, fecha_registro_max = row

print(f"Total pagos activos: {total:,}")
print(f"Fecha de pago mínima: {fecha_min}")
print(f"Fecha de pago máxima: {fecha_max}")
print(f"Fecha de registro mínima: {fecha_registro_min}")
print(f"Fecha de registro máxima: {fecha_registro_max}")

# 8. Resumen y conclusiones
print("\n8. RESUMEN Y CONCLUSIONES:")
print("-" * 80)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_pagos,
        COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS con_prestamo_id,
        COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS sin_prestamo_id,
        COUNT(CASE WHEN prestamo_id IS NULL AND cedula IS NOT NULL AND cedula != '' THEN 1 END) AS sin_prestamo_id_pero_con_cedula,
        COUNT(CASE WHEN prestamo_id IS NULL AND cedula IS NOT NULL AND cedula != '' AND EXISTS(
            SELECT 1 FROM prestamos pr WHERE pr.cedula = pagos.cedula AND pr.estado = 'APROBADO'
        ) THEN 1 END) AS deberian_tener_prestamo_id
    FROM pagos
    WHERE activo = TRUE
"""))

row = resultado.fetchone()
total, con_prestamo, sin_prestamo, sin_prestamo_con_cedula, deberian_tener = row

print(f"Total pagos activos: {total:,}")
print(f"Pagos con prestamo_id: {con_prestamo:,}")
print(f"Pagos sin prestamo_id: {sin_prestamo:,}")
print(f"Pagos sin prestamo_id pero CON cédula: {sin_prestamo_con_cedula:,}")
print(f"Pagos que DEBERIAN tener prestamo_id (tienen cédula y hay préstamo aprobado): {deberian_tener:,}")

if deberian_tener > 0:
    print(f"\n⚠️ PROBLEMA DETECTADO: {deberian_tener:,} pagos tienen cédula y hay préstamos aprobados disponibles,")
    print("   pero NO tienen prestamo_id asignado.")
    print("   Esto sugiere que:")
    print("   1. La migración no asignó prestamo_id automáticamente")
    print("   2. O el código de creación de pagos no está asignando prestamo_id correctamente")

print("\n" + "=" * 80)

db.close()
