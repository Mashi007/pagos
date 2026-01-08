"""Verificar que todos los préstamos tienen tabla de amortización (cuotas generadas)"""
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
print("VERIFICACION: PRESTAMOS CON TABLA DE AMORTIZACION")
print("=" * 70)
print("\nObjetivo: Verificar que todos los prestamos tienen cuotas generadas")
print("\n" + "=" * 70)

# 1. Resumen general
print("\n1. RESUMEN GENERAL:")
print("-" * 70)

# Total préstamos
resultado = db.execute(text("SELECT COUNT(*) FROM prestamos"))
total_prestamos = resultado.scalar()

# Préstamos aprobados
resultado = db.execute(text("SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO'"))
prestamos_aprobados = resultado.scalar()

# Préstamos con cuotas
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT p.id) 
        FROM prestamos p
        INNER JOIN cuotas cu ON p.id = cu.prestamo_id
    """)
)
prestamos_con_cuotas = resultado.scalar()

# Préstamos sin cuotas
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT p.id) 
        FROM prestamos p
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE cu.id IS NULL
    """)
)
prestamos_sin_cuotas = resultado.scalar()

# Préstamos aprobados con cuotas
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT p.id) 
        FROM prestamos p
        INNER JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
    """)
)
prestamos_aprobados_con_cuotas = resultado.scalar()

# Préstamos aprobados sin cuotas
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT p.id) 
        FROM prestamos p
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
          AND cu.id IS NULL
    """)
)
prestamos_aprobados_sin_cuotas = resultado.scalar()

print(f"\nTotal prestamos: {total_prestamos}")
print(f"  Prestamos APROBADOS: {prestamos_aprobados}")
print(f"\nPrestamos CON cuotas generadas: {prestamos_con_cuotas}")
print(f"Prestamos SIN cuotas generadas: {prestamos_sin_cuotas}")
print(f"\nPrestamos APROBADOS:")
print(f"  CON cuotas: {prestamos_aprobados_con_cuotas}")
print(f"  SIN cuotas: {prestamos_aprobados_sin_cuotas}")

# 2. Préstamos aprobados sin cuotas
print("\n" + "=" * 70)
print("2. PRESTAMOS APROBADOS SIN CUOTAS GENERADAS:")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            p.id AS prestamo_id,
            p.cedula,
            c.nombres AS nombre_cliente,
            p.estado AS estado_prestamo,
            p.total_financiamiento,
            p.numero_cuotas,
            p.cuota_periodo,
            p.modalidad_pago,
            p.tasa_interes,
            p.fecha_aprobacion,
            p.fecha_base_calculo,
            p.fecha_registro,
            CASE 
                WHEN p.fecha_base_calculo IS NULL THEN 'FALTA fecha_base_calculo'
                ELSE 'TIENE fecha_base_calculo'
            END AS tiene_fecha_base
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
          AND cu.id IS NULL
        ORDER BY p.fecha_aprobacion DESC, p.id
    """)
)

prestamos_sin_cuotas_lista = resultado.fetchall()

if len(prestamos_sin_cuotas_lista) == 0:
    print("\n[OK] Todos los prestamos APROBADOS tienen cuotas generadas")
else:
    print(f"\n[ATENCION] Se encontraron {len(prestamos_sin_cuotas_lista)} prestamos APROBADOS sin cuotas:")
    print("\nDetalle:")
    for i, prestamo in enumerate(prestamos_sin_cuotas_lista[:20], 1):
        prestamo_id, cedula, nombre, estado, total_fin, num_cuotas, cuota_periodo, modalidad, tasa, fecha_aprob, fecha_base, fecha_reg, tiene_fecha = prestamo
        print(f"\n  Prestamo {i}:")
        print(f"    ID: {prestamo_id}")
        print(f"    Cedula: {cedula}")
        if nombre:
            print(f"    Cliente: {nombre}")
        print(f"    Total financiamiento: ${total_fin:,.2f}")
        print(f"    Numero cuotas: {num_cuotas}")
        print(f"    Cuota periodo: ${cuota_periodo:,.2f}")
        print(f"    Modalidad: {modalidad}")
        print(f"    Tasa interes: {tasa}%")
        print(f"    Fecha aprobacion: {fecha_aprob}")
        print(f"    {tiene_fecha}")
    
    if len(prestamos_sin_cuotas_lista) > 20:
        print(f"\n  ... y {len(prestamos_sin_cuotas_lista) - 20} prestamos mas")

# 3. Préstamos sin fecha_base_calculo
print("\n" + "=" * 70)
print("3. PRESTAMOS SIN fecha_base_calculo (NO PUEDEN GENERAR CUOTAS):")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            p.id AS prestamo_id,
            p.cedula,
            c.nombres AS nombre_cliente,
            p.estado AS estado_prestamo,
            p.total_financiamiento,
            p.numero_cuotas,
            p.fecha_aprobacion
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula
        WHERE p.estado = 'APROBADO'
          AND p.fecha_base_calculo IS NULL
        ORDER BY p.fecha_aprobacion DESC
    """)
)

prestamos_sin_fecha_base = resultado.fetchall()

if len(prestamos_sin_fecha_base) == 0:
    print("\n[OK] Todos los prestamos APROBADOS tienen fecha_base_calculo")
else:
    print(f"\n[ATENCION] Se encontraron {len(prestamos_sin_fecha_base)} prestamos APROBADOS sin fecha_base_calculo:")
    for i, prestamo in enumerate(prestamos_sin_fecha_base[:10], 1):
        prestamo_id, cedula, nombre, estado, total_fin, num_cuotas, fecha_aprob = prestamo
        print(f"\n  Prestamo {i}: ID={prestamo_id}, Cedula={cedula}, Cliente={nombre or 'N/A'}")

# 4. Verificación de consistencia: cuotas generadas vs planificadas
print("\n" + "=" * 70)
print("4. VERIFICACION DE CONSISTENCIA (Cuotas generadas vs planificadas):")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            p.id AS prestamo_id,
            p.cedula,
            c.nombres AS nombre_cliente,
            p.numero_cuotas AS cuotas_planificadas,
            COALESCE(cuotas_count.cuotas_generadas, 0) AS cuotas_generadas,
            CASE 
                WHEN COALESCE(cuotas_count.cuotas_generadas, 0) = p.numero_cuotas THEN 'OK'
                WHEN COALESCE(cuotas_count.cuotas_generadas, 0) < p.numero_cuotas THEN 'FALTAN CUOTAS'
                WHEN COALESCE(cuotas_count.cuotas_generadas, 0) > p.numero_cuotas THEN 'CUOTAS DE MAS'
                ELSE 'SIN CUOTAS'
            END AS estado_cuotas
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula
        LEFT JOIN (
            SELECT 
                prestamo_id,
                COUNT(*) AS cuotas_generadas
            FROM cuotas
            GROUP BY prestamo_id
        ) cuotas_count ON p.id = cuotas_count.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, cuotas_count.cuotas_generadas
        HAVING COALESCE(cuotas_count.cuotas_generadas, 0) != p.numero_cuotas
        ORDER BY ABS(COALESCE(cuotas_count.cuotas_generadas, 0) - p.numero_cuotas) DESC, p.id
        LIMIT 20
    """)
)

inconsistencias = resultado.fetchall()

if len(inconsistencias) == 0:
    print("\n[OK] Todos los prestamos tienen el numero correcto de cuotas generadas")
else:
    print(f"\n[ATENCION] Se encontraron {len(inconsistencias)} prestamos con inconsistencias:")
    for i, inc in enumerate(inconsistencias, 1):
        prestamo_id, cedula, nombre, planificadas, generadas, estado = inc
        print(f"\n  Prestamo {i}:")
        print(f"    ID: {prestamo_id}")
        print(f"    Cedula: {cedula}")
        if nombre:
            print(f"    Cliente: {nombre}")
        print(f"    Cuotas planificadas: {planificadas}")
        print(f"    Cuotas generadas: {generadas}")
        print(f"    Estado: {estado}")

# 5. Verificación final
print("\n" + "=" * 70)
print("5. VERIFICACION FINAL:")
print("-" * 70)

if prestamos_aprobados_sin_cuotas == 0:
    print("\n[OK] VERIFICACION EXITOSA:")
    print("  Todos los prestamos APROBADOS tienen cuotas generadas")
    print("  La migracion se completo correctamente")
else:
    print(f"\n[ATENCION] VERIFICACION CON PROBLEMAS:")
    print(f"  Hay {prestamos_aprobados_sin_cuotas} prestamos APROBADOS sin cuotas generadas")
    print("\n  Acciones recomendadas:")
    print("  1. Ejecutar script: python scripts/python/Generar_Cuotas_Masivas.py")
    print("  2. O usar endpoint API: POST /api/v1/prestamos/{id}/generar-amortizacion")
    
    if len(prestamos_sin_fecha_base) > 0:
        print(f"\n  [CRITICO] {len(prestamos_sin_fecha_base)} prestamos no tienen fecha_base_calculo")
        print("  Estos prestamos NO pueden generar cuotas hasta que se les asigne fecha_base_calculo")

# Estadísticas adicionales
print("\n" + "=" * 70)
print("6. ESTADISTICAS ADICIONALES:")
print("-" * 70)

# Total de cuotas generadas
resultado = db.execute(text("SELECT COUNT(*) FROM cuotas"))
total_cuotas = resultado.scalar()

# Promedio de cuotas por préstamo
if prestamos_con_cuotas > 0:
    promedio_cuotas = total_cuotas / prestamos_con_cuotas
else:
    promedio_cuotas = 0

print(f"\nTotal cuotas generadas en BD: {total_cuotas}")
print(f"Promedio de cuotas por prestamo: {promedio_cuotas:.2f}")

# Distribución por modalidad
resultado = db.execute(
    text("""
        SELECT 
            p.modalidad_pago,
            COUNT(DISTINCT p.id) AS total_prestamos,
            COUNT(DISTINCT CASE WHEN cu.id IS NOT NULL THEN p.id END) AS prestamos_con_cuotas,
            COUNT(DISTINCT CASE WHEN cu.id IS NULL THEN p.id END) AS prestamos_sin_cuotas
        FROM prestamos p
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.modalidad_pago
        ORDER BY total_prestamos DESC
    """)
)

distribucion_modalidad = resultado.fetchall()
if distribucion_modalidad:
    print("\nDistribucion por modalidad de pago:")
    for modalidad, total, con_cuotas, sin_cuotas in distribucion_modalidad:
        print(f"  {modalidad}:")
        print(f"    Total prestamos: {total}")
        print(f"    Con cuotas: {con_cuotas}")
        print(f"    Sin cuotas: {sin_cuotas}")

print("\n" + "=" * 70)

db.close()
