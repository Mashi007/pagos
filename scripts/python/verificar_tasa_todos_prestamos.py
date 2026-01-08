"""Verificar tasa de interés de TODOS los préstamos"""
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
print("VERIFICACION: TASA DE INTERES DE TODOS LOS PRESTAMOS")
print("=" * 70)

# 1. Contar total de préstamos
print("\n1. TOTAL DE PRESTAMOS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_prestamos,
        COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados,
        COUNT(CASE WHEN estado != 'APROBADO' THEN 1 END) AS otros_estados
    FROM prestamos
"""))

row = resultado.fetchone()
total_prestamos, aprobados, otros_estados = row

print(f"Total préstamos: {total_prestamos:,}")
print(f"Préstamos APROBADOS: {aprobados:,}")
print(f"Préstamos otros estados: {otros_estados:,}")

# 2. Distribución de tasas de interés
print("\n2. DISTRIBUCION DE TASAS DE INTERES:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        tasa_interes,
        COUNT(*) AS cantidad,
        COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados,
        COUNT(CASE WHEN estado != 'APROBADO' THEN 1 END) AS otros_estados
    FROM prestamos
    GROUP BY tasa_interes
    ORDER BY tasa_interes
"""))

print(f"{'Tasa Interés':<15} {'Total':<12} {'Aprobados':<12} {'Otros Estados':<15}")
print("-" * 60)
for row in resultado.fetchall():
    tasa, cantidad, aprob, otros = row
    print(f"{tasa:<15} {cantidad:<12} {aprob:<12} {otros:<15}")

# 3. Verificar específicamente tasa 0%
print("\n3. PRESTAMOS CON TASA 0%:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_prestamos_tasa_cero,
        COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados_tasa_cero,
        COUNT(CASE WHEN estado != 'APROBADO' THEN 1 END) AS otros_estados_tasa_cero
    FROM prestamos
    WHERE tasa_interes = 0.00
"""))

row = resultado.fetchone()
total_tasa_cero, aprobados_tasa_cero, otros_estados_tasa_cero = row

print(f"Total préstamos con tasa 0%: {total_tasa_cero:,}")
print(f"Préstamos APROBADOS con tasa 0%: {aprobados_tasa_cero:,}")
print(f"Préstamos otros estados con tasa 0%: {otros_estados_tasa_cero:,}")

# 4. Verificar si TODOS tienen tasa 0%
print("\n4. CONFIRMACION:")
print("-" * 70)

if total_tasa_cero == total_prestamos:
    print("✅ CONFIRMADO: TODOS los préstamos tienen tasa 0%")
    print(f"   Total préstamos: {total_prestamos:,}")
    print(f"   Préstamos con tasa 0%: {total_tasa_cero:,}")
    print(f"   Coincidencia: 100%")
else:
    print("❌ NO CONFIRMADO: NO todos los préstamos tienen tasa 0%")
    print(f"   Total préstamos: {total_prestamos:,}")
    print(f"   Préstamos con tasa 0%: {total_tasa_cero:,}")
    print(f"   Préstamos con otra tasa: {total_prestamos - total_tasa_cero:,}")
    
    # Mostrar qué tasas tienen los que no son 0%
    resultado = db.execute(text("""
        SELECT 
            tasa_interes,
            COUNT(*) AS cantidad
        FROM prestamos
        WHERE tasa_interes != 0.00
        GROUP BY tasa_interes
        ORDER BY tasa_interes
    """))
    
    print("\n   Préstamos con tasas diferentes a 0%:")
    for row in resultado.fetchall():
        tasa, cantidad = row
        print(f"     - Tasa {tasa}%: {cantidad:,} préstamos")

# 5. Detalle por estado
print("\n5. DETALLE POR ESTADO:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        estado,
        COUNT(*) AS total,
        COUNT(CASE WHEN tasa_interes = 0.00 THEN 1 END) AS con_tasa_cero,
        COUNT(CASE WHEN tasa_interes != 0.00 THEN 1 END) AS con_otra_tasa
    FROM prestamos
    GROUP BY estado
    ORDER BY estado
"""))

print(f"{'Estado':<20} {'Total':<12} {'Tasa 0%':<12} {'Otra Tasa':<12}")
print("-" * 60)
for row in resultado.fetchall():
    estado, total, tasa_cero, otra_tasa = row
    print(f"{estado:<20} {total:<12} {tasa_cero:<12} {otra_tasa:<12}")

print("\n" + "=" * 70)

db.close()
