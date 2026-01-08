"""Verificar préstamos con tasa de interés 0%"""
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
print("VERIFICACION: PRESTAMOS CON TASA DE INTERES 0%")
print("=" * 70)

# 1. Contar préstamos con tasa 0%
print("\n1. PRESTAMOS CON TASA 0%:")
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
total_tasa_cero, aprobados_tasa_cero, otros_estados = row

print(f"Total préstamos con tasa 0%: {total_tasa_cero:,}")
print(f"Préstamos APROBADOS con tasa 0%: {aprobados_tasa_cero:,}")
print(f"Préstamos otros estados con tasa 0%: {otros_estados:,}")

# 2. Distribución por estado
print("\n2. DISTRIBUCION POR ESTADO:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        estado,
        COUNT(*) AS cantidad,
        MIN(id) AS id_minimo,
        MAX(id) AS id_maximo
    FROM prestamos
    WHERE tasa_interes = 0.00
    GROUP BY estado
    ORDER BY estado
"""))

print(f"{'Estado':<20} {'Cantidad':<12} {'Rango IDs':<20}")
print("-" * 60)
for row in resultado.fetchall():
    estado, cantidad, id_min, id_max = row
    rango = f"{id_min} - {id_max}" if id_min else "N/A"
    print(f"{estado:<20} {cantidad:<12} {rango:<20}")

# 3. Verificar si hay tasas diferentes en préstamos aprobados
print("\n3. DISTRIBUCION DE TASAS EN PRESTAMOS APROBADOS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        tasa_interes,
        COUNT(*) AS cantidad
    FROM prestamos
    WHERE estado = 'APROBADO'
    GROUP BY tasa_interes
    ORDER BY tasa_interes
    LIMIT 10
"""))

print(f"{'Tasa Interés':<15} {'Cantidad':<12}")
print("-" * 30)
for row in resultado.fetchall():
    tasa, cantidad = row
    print(f"{tasa:<15} {cantidad:<12}")

# 4. Verificar si hay una tasa por defecto configurada
print("\n4. TASA MAS COMUN EN PRESTAMOS APROBADOS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        tasa_interes,
        COUNT(*) AS cantidad
    FROM prestamos
    WHERE estado = 'APROBADO'
      AND tasa_interes > 0
    GROUP BY tasa_interes
    ORDER BY COUNT(*) DESC
    LIMIT 5
"""))

tasas_comunes = resultado.fetchall()
if tasas_comunes:
    print("Tasas más comunes en préstamos aprobados (excluyendo 0%):")
    print(f"{'Tasa Interés':<15} {'Cantidad':<12}")
    print("-" * 30)
    for row in tasas_comunes:
        tasa, cantidad = row
        print(f"{tasa:<15} {cantidad:<12}")
    
    tasa_mas_comun = tasas_comunes[0][0]
    print(f"\nTasa más común: {tasa_mas_comun}%")
else:
    print("No hay préstamos aprobados con tasa > 0%")
    tasa_mas_comun = None

# 5. Resumen
print("\n5. RESUMEN:")
print("-" * 70)

print(f"Préstamos con tasa 0%: {total_tasa_cero:,}")
print(f"  - Aprobados: {aprobados_tasa_cero:,}")
print(f"  - Otros estados: {otros_estados:,}")

if tasa_mas_comun:
    print(f"\nTasa más común en préstamos aprobados: {tasa_mas_comun}%")
    print(f"\n¿Deseas actualizar los préstamos con tasa 0% a {tasa_mas_comun}%?")
else:
    print("\n⚠️ No hay tasa de referencia disponible")
    print("   Necesitas especificar a qué tasa actualizar")

print("\n" + "=" * 70)

db.close()
