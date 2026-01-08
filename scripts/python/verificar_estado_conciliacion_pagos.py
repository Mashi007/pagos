"""Verificar estado de conciliación de todos los pagos"""
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

print("=" * 70)
print("VERIFICACION: ESTADO DE CONCILIACION DE TODOS LOS PAGOS")
print("=" * 70)

# 1. Contar total de pagos
print("\n1. TOTAL DE PAGOS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_pagos,
        COUNT(CASE WHEN activo = TRUE THEN 1 END) AS pagos_activos,
        COUNT(CASE WHEN activo = FALSE THEN 1 END) AS pagos_inactivos
    FROM pagos
"""))

row = resultado.fetchone()
total_pagos, pagos_activos, pagos_inactivos = row

print(f"Total pagos: {total_pagos:,}")
print(f"Pagos activos: {pagos_activos:,}")
print(f"Pagos inactivos: {pagos_inactivos:,}")

# 2. Distribución por estado de conciliación
print("\n2. ESTADO DE CONCILIACION:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_pagos,
        COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS conciliados,
        COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS no_conciliados,
        COUNT(CASE WHEN verificado_concordancia = 'SI' THEN 1 END) AS verificados_si,
        COUNT(CASE WHEN verificado_concordancia = 'NO' THEN 1 END) AS verificados_no,
        COUNT(CASE WHEN conciliado = TRUE OR verificado_concordancia = 'SI' THEN 1 END) AS conciliados_o_verificados
    FROM pagos
    WHERE activo = TRUE
"""))

row = resultado.fetchone()
total_activos, conciliados, no_conciliados, verificados_si, verificados_no, conciliados_o_verificados = row

print(f"Total pagos activos: {total_activos:,}")
print(f"Pagos conciliados (conciliado = TRUE): {conciliados:,}")
print(f"Pagos NO conciliados (conciliado = FALSE): {no_conciliados:,}")
print(f"Pagos verificados (verificado_concordancia = 'SI'): {verificados_si:,}")
print(f"Pagos NO verificados (verificado_concordancia = 'NO'): {verificados_no:,}")
print(f"Pagos conciliados O verificados: {conciliados_o_verificados:,}")

# 3. Verificar si TODOS están conciliados
print("\n3. CONFIRMACION:")
print("-" * 70)

if conciliados_o_verificados == total_activos:
    print("✅ CONFIRMADO: TODOS los pagos activos están conciliados o verificados")
    print(f"   Total pagos activos: {total_activos:,}")
    print(f"   Conciliados o verificados: {conciliados_o_verificados:,} (100%)")
else:
    print("❌ NO CONFIRMADO: NO todos los pagos están conciliados")
    print(f"   Total pagos activos: {total_activos:,}")
    print(f"   Conciliados o verificados: {conciliados_o_verificados:,}")
    print(f"   NO conciliados: {total_activos - conciliados_o_verificados:,}")

# 4. Distribución detallada
print("\n4. DISTRIBUCION DETALLADA:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        CASE 
            WHEN conciliado = TRUE THEN 'CONCILIADO'
            WHEN verificado_concordancia = 'SI' THEN 'VERIFICADO'
            ELSE 'NO CONCILIADO'
        END AS estado_conciliacion,
        COUNT(*) AS cantidad,
        COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS con_prestamo_id,
        COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS sin_prestamo_id
    FROM pagos
    WHERE activo = TRUE
    GROUP BY estado_conciliacion
    ORDER BY estado_conciliacion
"""))

print(f"{'Estado Conciliación':<20} {'Cantidad':<12} {'Con prestamo_id':<15} {'Sin prestamo_id':<15}")
print("-" * 70)
for row in resultado.fetchall():
    estado, cantidad, con_prestamo, sin_prestamo = row
    print(f"{estado:<20} {cantidad:<12} {con_prestamo:<15} {sin_prestamo:<15}")

# 5. Pagos con prestamo_id vs sin prestamo_id
print("\n5. PAGOS CON Y SIN prestamo_id:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_pagos,
        COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS con_prestamo_id,
        COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS sin_prestamo_id,
        COUNT(CASE WHEN prestamo_id IS NOT NULL AND (conciliado = TRUE OR verificado_concordancia = 'SI') THEN 1 END) AS con_prestamo_conciliados,
        COUNT(CASE WHEN prestamo_id IS NULL AND (conciliado = TRUE OR verificado_concordancia = 'SI') THEN 1 END) AS sin_prestamo_conciliados
    FROM pagos
    WHERE activo = TRUE
"""))

row = resultado.fetchone()
total, con_prestamo, sin_prestamo, con_prestamo_conciliados, sin_prestamo_conciliados = row

print(f"Total pagos activos: {total:,}")
print(f"Pagos con prestamo_id: {con_prestamo:,}")
print(f"  - Conciliados o verificados: {con_prestamo_conciliados:,}")
print(f"  - NO conciliados: {con_prestamo - con_prestamo_conciliados:,}")
print(f"Pagos sin prestamo_id: {sin_prestamo:,}")
print(f"  - Conciliados o verificados: {sin_prestamo_conciliados:,}")
print(f"  - NO conciliados: {sin_prestamo - sin_prestamo_conciliados:,}")

# 6. Resumen final
print("\n6. RESUMEN FINAL:")
print("-" * 70)

porcentaje_conciliados = (conciliados_o_verificados / total_activos * 100) if total_activos > 0 else 0

print(f"Total pagos activos: {total_activos:,}")
print(f"Pagos conciliados o verificados: {conciliados_o_verificados:,} ({porcentaje_conciliados:.2f}%)")
print(f"Pagos NO conciliados: {total_activos - conciliados_o_verificados:,} ({100 - porcentaje_conciliados:.2f}%)")

if conciliados_o_verificados == total_activos:
    print("\n✅ CONFIRMADO: Todos los pagos activos están conciliados o verificados")
    print("   Esto es consistente con una migración donde todos los pagos vienen conciliados")
else:
    print(f"\n⚠️ NO CONFIRMADO: Hay {total_activos - conciliados_o_verificados:,} pagos activos sin conciliar")
    print("   Puede ser que no todos los pagos migrados venían conciliados")

print("\n" + "=" * 70)

db.close()
