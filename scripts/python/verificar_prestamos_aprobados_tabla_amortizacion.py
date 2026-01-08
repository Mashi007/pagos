"""Verificar que todos los préstamos aprobados tengan tabla de amortización (cuotas)"""
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
print("VERIFICACION: PRESTAMOS APROBADOS Y TABLA DE AMORTIZACION")
print("=" * 70)
print("Regla de negocio: Todos los préstamos APROBADOS deben tener cuotas generadas")
print("=" * 70)

# ======================================================================
# 1. VERIFICAR PRESTAMOS APROBADOS SIN CUOTAS
# ======================================================================

print("\n1. PRESTAMOS APROBADOS SIN CUOTAS GENERADAS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        p.id AS prestamo_id,
        p.cedula,
        p.nombres,
        p.numero_cuotas AS cuotas_planificadas,
        p.fecha_base_calculo,
        p.estado,
        COUNT(c.id) AS cuotas_generadas
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
    GROUP BY p.id, p.cedula, p.nombres, p.numero_cuotas, p.fecha_base_calculo, p.estado
    HAVING COUNT(c.id) = 0
    ORDER BY p.id
"""))

prestamos_sin_cuotas = resultado.fetchall()

if prestamos_sin_cuotas:
    print(f"⚠️ ERROR: Se encontraron {len(prestamos_sin_cuotas)} préstamos APROBADOS SIN cuotas:")
    print(f"{'Prestamo ID':<12} {'Cedula':<15} {'Nombres':<35} {'Cuotas Plan':<12} {'Fecha Base':<12}")
    print("-" * 100)
    
    for row in prestamos_sin_cuotas:
        prestamo_id, cedula, nombres, cuotas_plan, fecha_base, estado, cuotas_gen = row
        nombres_str = nombres[:33] + ".." if nombres and len(nombres) > 35 else (nombres or "N/A")
        fecha_str = str(fecha_base) if fecha_base else "SIN FECHA"
        print(f"{prestamo_id:<12} {cedula:<15} {nombres_str:<35} {cuotas_plan:<12} {fecha_str:<12}")
    
    print(f"\n❌ VIOLACION DE REGLA DE NEGOCIO:")
    print(f"   Estos {len(prestamos_sin_cuotas)} préstamos están APROBADOS pero NO tienen cuotas generadas")
    print(f"   DEBEN generar tabla de amortización")
else:
    print("✅ CORRECTO: Todos los préstamos APROBADOS tienen cuotas generadas")

# ======================================================================
# 2. VERIFICAR PRESTAMOS APROBADOS CON fecha_base_calculo NULL
# ======================================================================

print("\n2. PRESTAMOS APROBADOS SIN fecha_base_calculo:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        p.id AS prestamo_id,
        p.cedula,
        p.nombres,
        p.numero_cuotas,
        p.fecha_base_calculo,
        COUNT(c.id) AS cuotas_generadas
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO' AND p.fecha_base_calculo IS NULL
    GROUP BY p.id, p.cedula, p.nombres, p.numero_cuotas, p.fecha_base_calculo
    ORDER BY p.id
    LIMIT 20
"""))

prestamos_sin_fecha = resultado.fetchall()

if prestamos_sin_fecha:
    print(f"⚠️ Se encontraron {len(prestamos_sin_fecha)} préstamos APROBADOS sin fecha_base_calculo:")
    print(f"{'Prestamo ID':<12} {'Cedula':<15} {'Nombres':<35} {'Cuotas Plan':<12} {'Cuotas Gen':<12}")
    print("-" * 100)
    
    for row in prestamos_sin_fecha:
        prestamo_id, cedula, nombres, cuotas_plan, fecha_base, cuotas_gen = row
        nombres_str = nombres[:33] + ".." if nombres and len(nombres) > 35 else (nombres or "N/A")
        print(f"{prestamo_id:<12} {cedula:<15} {nombres_str:<35} {cuotas_plan:<12} {cuotas_gen:<12}")
    
    print(f"\n⚠️ ADVERTENCIA: Sin fecha_base_calculo no se pueden generar cuotas correctamente")
    
    # Contar total
    resultado_total = db.execute(text("""
        SELECT COUNT(*)
        FROM prestamos
        WHERE estado = 'APROBADO' AND fecha_base_calculo IS NULL
    """))
    total_sin_fecha = resultado_total.scalar()
    print(f"Total préstamos aprobados sin fecha_base_calculo: {total_sin_fecha}")
else:
    print("✅ CORRECTO: Todos los préstamos APROBADOS tienen fecha_base_calculo")

# ======================================================================
# 3. RESUMEN GENERAL
# ======================================================================

print("\n3. RESUMEN GENERAL:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_aprobados,
        COUNT(CASE WHEN fecha_base_calculo IS NOT NULL THEN 1 END) AS con_fecha_base,
        COUNT(CASE WHEN fecha_base_calculo IS NULL THEN 1 END) AS sin_fecha_base
    FROM prestamos
    WHERE estado = 'APROBADO'
"""))

row = resultado.fetchone()
total_aprobados, con_fecha, sin_fecha = row

print(f"Total préstamos APROBADOS: {total_aprobados:,}")
print(f"Con fecha_base_calculo: {con_fecha:,}")
print(f"Sin fecha_base_calculo: {sin_fecha:,}")

# Verificar cuotas
resultado_cuotas = db.execute(text("""
    SELECT 
        COUNT(DISTINCT p.id) AS prestamos_con_cuotas,
        COUNT(c.id) AS total_cuotas_generadas
    FROM prestamos p
    INNER JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
"""))

row_cuotas = resultado_cuotas.fetchone()
prestamos_con_cuotas, total_cuotas = row_cuotas

print(f"\nPréstamos APROBADOS con cuotas: {prestamos_con_cuotas:,}")
print(f"Total cuotas generadas: {total_cuotas:,}")

diferencia = total_aprobados - prestamos_con_cuotas
if diferencia > 0:
    print(f"\n❌ ERROR: {diferencia} préstamos APROBADOS NO tienen cuotas generadas")
else:
    print(f"\n✅ CORRECTO: Todos los préstamos APROBADOS tienen cuotas generadas")

# ======================================================================
# 4. VERIFICAR CONSISTENCIA: CUOTAS GENERADAS VS PLANIFICADAS
# ======================================================================

print("\n4. CONSISTENCIA: CUOTAS GENERADAS VS PLANIFICADAS:")
print("-" * 70)

resultado = db.execute(text("""
    WITH prestamos_cuotas AS (
        SELECT 
            p.id,
            p.numero_cuotas,
            COUNT(c.id) AS cuotas_generadas
        FROM prestamos p
        LEFT JOIN cuotas c ON p.id = c.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.numero_cuotas
    )
    SELECT 
        COUNT(*) AS total_prestamos,
        COUNT(CASE WHEN cuotas_generadas = numero_cuotas THEN 1 END) AS prestamos_ok,
        COUNT(CASE WHEN cuotas_generadas < numero_cuotas THEN 1 END) AS prestamos_faltan_cuotas,
        COUNT(CASE WHEN cuotas_generadas > numero_cuotas THEN 1 END) AS prestamos_cuotas_extra,
        COUNT(CASE WHEN cuotas_generadas = 0 THEN 1 END) AS prestamos_sin_cuotas
    FROM prestamos_cuotas
"""))

row = resultado.fetchone()
total_prestamos, prestamos_ok, prestamos_faltan, prestamos_extra, prestamos_sin_cuotas = row

print(f"Total préstamos analizados: {total_prestamos:,}")
print(f"Préstamos con cuotas correctas: {prestamos_ok:,}")
print(f"Préstamos con cuotas faltantes: {prestamos_faltan:,}")
print(f"Préstamos con cuotas extra: {prestamos_extra:,}")
print(f"Préstamos sin cuotas: {prestamos_sin_cuotas:,}")

if prestamos_sin_cuotas > 0:
    print(f"\n❌ ERROR: {prestamos_sin_cuotas} préstamos APROBADOS NO tienen cuotas generadas")
    print("   VIOLACION DE REGLA DE NEGOCIO")
elif prestamos_faltan > 0 or prestamos_extra > 0:
    print(f"\n⚠️ ADVERTENCIA: Hay inconsistencias en el número de cuotas")
    print(f"   - {prestamos_faltan} préstamos tienen menos cuotas de las planificadas")
    print(f"   - {prestamos_extra} préstamos tienen más cuotas de las planificadas")
else:
    print("\n✅ CORRECTO: Todos los préstamos tienen el número correcto de cuotas")

# ======================================================================
# 5. CONCLUSION Y REGLA DE NEGOCIO
# ======================================================================

print("\n5. CONCLUSION Y REGLA DE NEGOCIO:")
print("-" * 70)

print("\n📋 REGLA DE NEGOCIO:")
print("   'Todos los préstamos con estado APROBADO deben tener tabla de amortización'")
print("   'Esto significa que deben tener cuotas generadas iguales a numero_cuotas'")

print("\n✅ VERIFICACION:")
if prestamos_sin_cuotas == 0 and prestamos_faltan == 0 and prestamos_extra == 0:
    print("   ✅ REGLA CUMPLIDA: Todos los préstamos APROBADOS tienen cuotas correctas")
    print(f"   ✅ {prestamos_ok:,} préstamos cumplen la regla")
else:
    print("   ❌ REGLA VIOLADA:")
    if prestamos_sin_cuotas > 0:
        print(f"      - {prestamos_sin_cuotas} préstamos APROBADOS NO tienen cuotas")
    if prestamos_faltan > 0:
        print(f"      - {prestamos_faltan} préstamos tienen menos cuotas de las planificadas")
    if prestamos_extra > 0:
        print(f"      - {prestamos_extra} préstamos tienen más cuotas de las planificadas")
    
    print("\n   ACCION REQUERIDA:")
    print("   - Generar tabla de amortización para préstamos sin cuotas")
    print("   - Corregir inconsistencias en número de cuotas")

print("\n" + "=" * 70)

db.close()
