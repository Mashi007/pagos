"""Verificar relación completa entre prestamos y cuotas"""
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
print("RELACION COMPLETA: PRESTAMOS Y CUOTAS")
print("=" * 70)

# 1. Cuotas con préstamos válidos
print("\n1. CUOTAS CON PRESTAMOS VALIDOS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT COUNT(*) 
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
"""))
cuotas_validas = resultado.scalar()

resultado = db.execute(text("""
    SELECT COUNT(*) 
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.estado = 'APROBADO'
"""))
cuotas_aprobados = resultado.scalar()

print(f"Cuotas con prestamo valido: {cuotas_validas}")
print(f"Cuotas de prestamos aprobados: {cuotas_aprobados}")

# 2. Cuotas huérfanas
print("\n2. CUOTAS HUERFANAS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT COUNT(*) 
    FROM cuotas c
    LEFT JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.id IS NULL
"""))
cuotas_huerfanas = resultado.scalar()

print(f"Cuotas huérfanas (sin prestamo valido): {cuotas_huerfanas}")

if cuotas_huerfanas > 0:
    resultado = db.execute(text("""
        SELECT DISTINCT c.prestamo_id
        FROM cuotas c
        LEFT JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.id IS NULL
        ORDER BY c.prestamo_id
        LIMIT 10
    """))
    ids_huerfanos = [row[0] for row in resultado.fetchall()]
    print(f"Ejemplos de prestamo_id inexistentes: {ids_huerfanos}")

# 3. Rango de IDs
print("\n3. RANGOS DE IDs:")
print("-" * 70)

resultado = db.execute(text("SELECT MIN(id), MAX(id) FROM prestamos"))
min_p, max_p = resultado.fetchone()

resultado = db.execute(text("SELECT MIN(prestamo_id), MAX(prestamo_id) FROM cuotas"))
min_c, max_c = resultado.fetchone()

print(f"Prestamos ID: {min_p} - {max_p}")
print(f"Cuotas prestamo_id: {min_c} - {max_c}")

# 4. Resumen final
print("\n4. RESUMEN FINAL:")
print("-" * 70)

resultado = db.execute(text("SELECT COUNT(*) FROM cuotas"))
total_cuotas = resultado.scalar()

resultado = db.execute(text("SELECT COUNT(*) FROM prestamos"))
total_prestamos = resultado.scalar()

print(f"Total cuotas en BD: {total_cuotas}")
print(f"Total prestamos en BD: {total_prestamos}")
print(f"Cuotas con prestamo valido: {cuotas_validas}")
print(f"Cuotas huérfanas: {cuotas_huerfanas}")

if cuotas_huerfanas == 0:
    print("\n[OK] Todas las cuotas tienen prestamo valido")
else:
    print(f"\n[ADVERTENCIA] Hay {cuotas_huerfanas} cuotas huérfanas")
    print("  Estas cuotas tienen prestamo_id que no existe en la tabla prestamos")
    print("  Pueden ser de préstamos eliminados o datos migrados")

print("\n" + "=" * 70)

db.close()
