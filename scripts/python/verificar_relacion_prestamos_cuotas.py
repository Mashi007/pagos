"""Verificar relación entre tablas prestamos y cuotas"""
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
print("RELACION ENTRE TABLAS PRESTAMOS Y CUOTAS")
print("=" * 70)

# 1. Verificar Foreign Key
print("\n1. FOREIGN KEY:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        tc.table_name AS tabla_hija,
        kcu.column_name AS columna_fk,
        ccu.table_name AS tabla_padre,
        ccu.column_name AS columna_pk,
        tc.constraint_name AS nombre_fk
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = 'cuotas'
        AND ccu.table_name = 'prestamos'
"""))

fks = resultado.fetchall()
if len(fks) > 0:
    for fk in fks:
        tabla_hija, col_fk, tabla_padre, col_pk, nombre_fk = fk
        print(f"  {tabla_hija}.{col_fk} → {tabla_padre}.{col_pk}")
        print(f"    Constraint: {nombre_fk}")
else:
    print("  [ADVERTENCIA] No se encontró Foreign Key definido")

# 2. Resumen de la relación
print("\n2. RESUMEN DE LA RELACION:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(DISTINCT p.id) AS total_prestamos,
        COUNT(DISTINCT c.id) AS total_cuotas,
        COUNT(DISTINCT c.prestamo_id) AS prestamos_con_cuotas,
        COUNT(DISTINCT p.id) - COUNT(DISTINCT c.prestamo_id) AS prestamos_sin_cuotas
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
"""))

row = resultado.fetchone()
total_prestamos, total_cuotas, prestamos_con_cuotas, prestamos_sin_cuotas = row

print(f"Total prestamos: {total_prestamos}")
print(f"Total cuotas: {total_cuotas}")
print(f"Prestamos con cuotas: {prestamos_con_cuotas}")
print(f"Prestamos sin cuotas: {prestamos_sin_cuotas}")

if total_prestamos > 0:
    promedio = total_cuotas / total_prestamos
    print(f"Promedio cuotas por prestamo: {promedio:.2f}")

# 3. Verificar integridad referencial
print("\n3. INTEGRIDAD REFERENCIAL:")
print("-" * 70)

# Cuotas huérfanas (sin préstamo válido)
resultado = db.execute(text("""
    SELECT COUNT(*)
    FROM cuotas c
    LEFT JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.id IS NULL
"""))
cuotas_huerfanas = resultado.scalar()

# Préstamos sin cuotas (aprobados)
resultado = db.execute(text("""
    SELECT COUNT(*)
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE c.id IS NULL AND p.estado = 'APROBADO'
"""))
prestamos_sin_cuotas_aprobados = resultado.scalar()

print(f"Cuotas huérfanas (sin prestamo valido): {cuotas_huerfanas}")
print(f"Prestamos aprobados sin cuotas: {prestamos_sin_cuotas_aprobados}")

if cuotas_huerfanas == 0 and prestamos_sin_cuotas_aprobados == 0:
    print("\n[OK] Integridad referencial correcta")
else:
    print("\n[ERROR] Problemas de integridad referencial detectados")

# 4. Estructura de la relación
print("\n4. ESTRUCTURA DE LA RELACION:")
print("-" * 70)
print("Tipo: Uno a Muchos (1:N)")
print("  1 Prestamo → N Cuotas")
print("\nCampos de relación:")
print("  - prestamos.id (PK)")
print("  - cuotas.prestamo_id (FK → prestamos.id)")
print("\nCampos relacionados:")
print("  - prestamos.numero_cuotas: Número de cuotas planificadas")
print("  - cuotas.numero_cuota: Número de cuota (1, 2, 3, ...)")
print("  - prestamos.fecha_base_calculo: Fecha base para calcular vencimientos")
print("  - cuotas.fecha_vencimiento: Fecha calculada desde fecha_base_calculo")

# 5. Ejemplo de relación
print("\n5. EJEMPLO DE RELACION:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        p.id AS prestamo_id,
        p.cedula,
        p.nombres,
        p.numero_cuotas AS cuotas_planificadas,
        COUNT(c.id) AS cuotas_generadas,
        MIN(c.numero_cuota) AS primera_cuota,
        MAX(c.numero_cuota) AS ultima_cuota
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
    GROUP BY p.id, p.cedula, p.nombres, p.numero_cuotas
    HAVING COUNT(c.id) > 0
    ORDER BY p.id
    LIMIT 5
"""))

ejemplos = resultado.fetchall()
if len(ejemplos) > 0:
    print("\nEjemplos de préstamos con sus cuotas:")
    for i, ej in enumerate(ejemplos, 1):
        prestamo_id, cedula, nombres, planificadas, generadas, primera, ultima = ej
        print(f"\n  Prestamo {i}:")
        print(f"    ID: {prestamo_id}")
        print(f"    Cedula: {cedula}")
        print(f"    Cliente: {nombres}")
        print(f"    Cuotas planificadas: {planificadas}")
        print(f"    Cuotas generadas: {generadas}")
        print(f"    Rango de cuotas: {primera} - {ultima}")

print("\n" + "=" * 70)

db.close()
