"""Verificar que los préstamos aprobados tienen cuotas propias y no están afectados por huérfanas"""
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
print("VERIFICACION: CUOTAS PROPIAS VS HUERFANAS")
print("=" * 70)
print("Objetivo: Confirmar que los 4,042 préstamos tienen cuotas propias")
print("          y que las huérfanas NO los afectan")
print("=" * 70)

# ======================================================================
# 1. VERIFICAR CUOTAS DE PRESTAMOS APROBADOS (IDs 3785-7826)
# ======================================================================

print("\n1. CUOTAS DE PRESTAMOS APROBADOS (IDs 3785-7826):")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(DISTINCT p.id) AS prestamos_con_cuotas,
        COUNT(c.id) AS total_cuotas_propias,
        MIN(c.prestamo_id) AS prestamo_id_minimo,
        MAX(c.prestamo_id) AS prestamo_id_maximo,
        MIN(p.id) AS prestamo_id_min,
        MAX(p.id) AS prestamo_id_max
    FROM prestamos p
    INNER JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
"""))

row = resultado.fetchone()
prestamos_con_cuotas, total_cuotas_propias, cuota_prestamo_min, cuota_prestamo_max, prestamo_min, prestamo_max = row

print(f"Préstamos aprobados con cuotas: {prestamos_con_cuotas:,}")
print(f"Total cuotas propias: {total_cuotas_propias:,}")
print(f"Rango de prestamo_id en cuotas: {cuota_prestamo_min} - {cuota_prestamo_max}")
print(f"Rango de IDs de préstamos: {prestamo_min} - {prestamo_max}")

if cuota_prestamo_min >= 3785 and cuota_prestamo_max <= 7826:
    print("\n✅ CONFIRMADO: Todas las cuotas de préstamos aprobados tienen prestamo_id entre 3785-7826")
    print("   Las cuotas son propias de los préstamos aprobados")
else:
    print(f"\n⚠️ ADVERTENCIA: Hay cuotas con prestamo_id fuera del rango 3785-7826")
    print(f"   Rango encontrado: {cuota_prestamo_min} - {cuota_prestamo_max}")

# ======================================================================
# 2. VERIFICAR CUOTAS HUERFANAS (prestamo_id 1-3784)
# ======================================================================

print("\n2. CUOTAS HUERFANAS (prestamo_id 1-3784):")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_cuotas_huerfanas,
        COUNT(DISTINCT prestamo_id) AS prestamos_referenciados,
        MIN(prestamo_id) AS prestamo_id_minimo,
        MAX(prestamo_id) AS prestamo_id_maximo,
        COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_pagos,
        SUM(total_pagado) AS total_pagado
    FROM cuotas
    WHERE prestamo_id BETWEEN 1 AND 3784
"""))

row = resultado.fetchone()
total_huerfanas, prestamos_ref, min_id, max_id, cuotas_pagos, total_pagado = row

print(f"Total cuotas huérfanas: {total_huerfanas:,}")
print(f"Prestamos referenciados: {prestamos_ref:,}")
print(f"Rango de prestamo_id: {min_id} - {max_id}")
print(f"Cuotas con pagos: {cuotas_pagos:,}")
print(f"Total pagado: ${total_pagado:,.2f}" if total_pagado else "Total pagado: $0.00")

if min_id >= 1 and max_id <= 3784:
    print("\n✅ CONFIRMADO: Las cuotas huérfanas tienen prestamo_id entre 1-3784")
    print("   Estas cuotas NO afectan a los préstamos aprobados (3785-7826)")
else:
    print(f"\n⚠️ ADVERTENCIA: Rango inesperado en cuotas huérfanas")

# ======================================================================
# 3. VERIFICAR QUE NO HAY SOLAPAMIENTO
# ======================================================================

print("\n3. VERIFICAR SOLAPAMIENTO ENTRE CUOTAS PROPIAS Y HUERFANAS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS cuotas_solapadas
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.estado = 'APROBADO'
      AND c.prestamo_id BETWEEN 1 AND 3784
"""))

cuotas_solapadas = resultado.scalar()

if cuotas_solapadas == 0:
    print("✅ CONFIRMADO: NO hay solapamiento")
    print("   Las cuotas con prestamo_id 1-3784 NO pertenecen a préstamos aprobados")
    print("   Las cuotas de préstamos aprobados tienen prestamo_id 3785-7826")
else:
    print(f"⚠️ ADVERTENCIA: Se encontraron {cuotas_solapadas} cuotas que solapan")
    print("   Hay cuotas con prestamo_id 1-3784 que pertenecen a préstamos aprobados")

# ======================================================================
# 4. VERIFICAR QUE LOS PRESTAMOS APROBADOS NO DEPENDEN DE CUOTAS HUERFANAS
# ======================================================================

print("\n4. VERIFICAR INDEPENDENCIA DE PRESTAMOS APROBADOS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS prestamos_afectados
    FROM prestamos p
    WHERE p.estado = 'APROBADO'
      AND p.id BETWEEN 3785 AND 7826
      AND NOT EXISTS (
          SELECT 1 
          FROM cuotas c 
          WHERE c.prestamo_id = p.id 
            AND c.prestamo_id BETWEEN 3785 AND 7826
      )
"""))

prestamos_afectados = resultado.scalar()

if prestamos_afectados == 0:
    print("✅ CONFIRMADO: Todos los préstamos aprobados tienen cuotas propias")
    print("   NO dependen de cuotas huérfanas")
else:
    print(f"⚠️ ADVERTENCIA: {prestamos_afectados} préstamos aprobados NO tienen cuotas propias")

# Verificar que todos tienen cuotas en el rango correcto
resultado = db.execute(text("""
    SELECT 
        COUNT(DISTINCT p.id) AS prestamos_con_cuotas_propias
    FROM prestamos p
    INNER JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
      AND p.id BETWEEN 3785 AND 7826
      AND c.prestamo_id BETWEEN 3785 AND 7826
"""))

prestamos_con_cuotas_propias = resultado.scalar()
print(f"\nPréstamos aprobados con cuotas propias (rango 3785-7826): {prestamos_con_cuotas_propias:,}")

# ======================================================================
# 5. RESUMEN FINAL Y RECOMENDACION
# ======================================================================

print("\n5. RESUMEN FINAL:")
print("-" * 70)

print(f"\n📊 CUOTAS PROPIAS DE PRESTAMOS APROBADOS:")
print(f"   - Total: {total_cuotas_propias:,}")
print(f"   - Rango prestamo_id: {cuota_prestamo_min} - {cuota_prestamo_max}")
print(f"   - Préstamos cubiertos: {prestamos_con_cuotas_propias:,} de 4,042")

print(f"\n📊 CUOTAS HUERFANAS:")
print(f"   - Total: {total_huerfanas:,}")
print(f"   - Rango prestamo_id: {min_id} - {max_id}")
print(f"   - Con pagos: {cuotas_pagos:,} (${total_pagado:,.2f})")

print(f"\n📊 VERIFICACIONES:")
print(f"   - Solapamiento: {'NO' if cuotas_solapadas == 0 else 'SI'}")
print(f"   - Independencia: {'CONFIRMADA' if prestamos_afectados == 0 else 'NO CONFIRMADA'}")

print("\n6. CONCLUSION:")
print("-" * 70)

if (cuotas_solapadas == 0 and 
    prestamos_afectados == 0 and 
    prestamos_con_cuotas_propias == 4042 and
    cuota_prestamo_min >= 3785 and 
    cuota_prestamo_max <= 7826):
    
    print("✅ CONFIRMADO: Los 4,042 préstamos aprobados tienen cuotas propias")
    print("✅ CONFIRMADO: Las cuotas huérfanas NO afectan a los préstamos aprobados")
    print("✅ CONFIRMADO: Las cuotas huérfanas son completamente independientes")
    print("\n✅ SEGURO ELIMINAR: Las cuotas huérfanas pueden eliminarse sin afectar")
    print("   los préstamos aprobados")
    
    if cuotas_pagos > 0:
        print(f"\n⚠️ ADVERTENCIA: {cuotas_pagos:,} cuotas huérfanas tienen pagos (${total_pagado:,.2f})")
        print("   ¿Deseas eliminar estas cuotas también?")
        print("   - Si son datos históricos importantes, considerar mantenerlas")
        print("   - Si son datos obsoletos, pueden eliminarse")
else:
    print("❌ NO CONFIRMADO: Hay problemas de solapamiento o dependencia")
    print("   NO eliminar cuotas huérfanas hasta resolver estos problemas")

print("\n" + "=" * 70)

db.close()
