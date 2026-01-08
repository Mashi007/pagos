"""Conciliación de préstamos aprobados: verificar duplicados y huérfanos"""
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
print("CONCILIACION: PRESTAMOS APROBADOS")
print("=" * 70)
print("Objetivo: Verificar duplicados y huérfanos antes de restaurar")
print("=" * 70)

# ======================================================================
# 1. RESUMEN GENERAL DE PRESTAMOS APROBADOS
# ======================================================================

print("\n1. RESUMEN GENERAL DE PRESTAMOS APROBADOS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_prestamos_aprobados,
        COUNT(DISTINCT id) AS prestamos_unicos,
        MIN(id) AS id_minimo,
        MAX(id) AS id_maximo,
        COUNT(DISTINCT cedula) AS clientes_unicos
    FROM prestamos
    WHERE estado = 'APROBADO'
"""))

row = resultado.fetchone()
total_aprobados, unicos, id_min, id_max, clientes_unicos = row

print(f"Total préstamos APROBADOS: {total_aprobados:,}")
print(f"Préstamos únicos (sin duplicados): {unicos:,}")
print(f"Rango de IDs: {id_min} - {id_max}")
print(f"Clientes únicos: {clientes_unicos:,}")

if total_aprobados != unicos:
    print(f"\n⚠️ ADVERTENCIA: Hay {total_aprobados - unicos} préstamos duplicados (mismo ID)")
else:
    print("\n✅ No hay préstamos duplicados por ID")

# ======================================================================
# 2. VERIFICAR PRESTAMOS DUPLICADOS POR ID
# ======================================================================

print("\n2. VERIFICAR PRESTAMOS DUPLICADOS POR ID:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        id,
        COUNT(*) AS cantidad,
        STRING_AGG(DISTINCT estado::TEXT, ', ') AS estados,
        STRING_AGG(DISTINCT cedula, ', ') AS cedulas
    FROM prestamos
    GROUP BY id
    HAVING COUNT(*) > 1
    ORDER BY id
    LIMIT 20
"""))

duplicados = resultado.fetchall()
if duplicados:
    print(f"⚠️ Se encontraron {len(duplicados)} IDs duplicados:")
    print(f"{'ID':<10} {'Cantidad':<10} {'Estados':<20} {'Cedulas':<30}")
    print("-" * 80)
    for row in duplicados:
        prestamo_id, cantidad, estados, cedulas = row
        cedulas_str = cedulas[:28] + ".." if len(cedulas) > 30 else cedulas
        print(f"{prestamo_id:<10} {cantidad:<10} {estados:<20} {cedulas_str:<30}")
else:
    print("✅ No hay préstamos duplicados por ID")

# ======================================================================
# 3. VERIFICAR PRESTAMOS APROBADOS SIN CUOTAS (HUERFANOS)
# ======================================================================

print("\n3. PRESTAMOS APROBADOS SIN CUOTAS (HUERFANOS):")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        p.id AS prestamo_id,
        p.cedula,
        p.nombres,
        p.numero_cuotas AS cuotas_planificadas,
        p.estado,
        p.fecha_base_calculo,
        COUNT(c.id) AS cuotas_generadas
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
    GROUP BY p.id, p.cedula, p.nombres, p.numero_cuotas, p.estado, p.fecha_base_calculo
    HAVING COUNT(c.id) = 0
    ORDER BY p.id
    LIMIT 20
"""))

prestamos_sin_cuotas = resultado.fetchall()
if prestamos_sin_cuotas:
    print(f"⚠️ Se encontraron {len(prestamos_sin_cuotas)} préstamos aprobados SIN cuotas:")
    print(f"{'Prestamo ID':<12} {'Cedula':<15} {'Nombres':<30} {'Cuotas Plan':<12} {'Fecha Base':<12}")
    print("-" * 90)
    for row in prestamos_sin_cuotas:
        prestamo_id, cedula, nombres, cuotas_plan, estado, fecha_base, cuotas_gen = row
        nombres_str = nombres[:28] + ".." if nombres and len(nombres) > 30 else (nombres or "N/A")
        fecha_str = str(fecha_base) if fecha_base else "N/A"
        print(f"{prestamo_id:<12} {cedula:<15} {nombres_str:<30} {cuotas_plan:<12} {fecha_str:<12}")
    
    # Contar total
    resultado_total = db.execute(text("""
        SELECT COUNT(*)
        FROM prestamos p
        LEFT JOIN cuotas c ON p.id = c.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id
        HAVING COUNT(c.id) = 0
    """))
    total_sin_cuotas = len(resultado_total.fetchall())
    print(f"\nTotal préstamos aprobados sin cuotas: {total_sin_cuotas}")
else:
    print("✅ Todos los préstamos aprobados tienen cuotas generadas")

# ======================================================================
# 4. VERIFICAR CUOTAS HUERFANAS (SIN PRESTAMO APROBADO)
# ======================================================================

print("\n4. CUOTAS HUERFANAS (SIN PRESTAMO APROBADO):")
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
    LEFT JOIN prestamos p ON c.prestamo_id = p.id AND p.estado = 'APROBADO'
    WHERE p.id IS NULL
"""))

row = resultado.fetchone()
total_huerfanas, prestamos_inexistentes, min_id, max_id, total_pagado, cuotas_con_pagos = row

print(f"Total cuotas huérfanas: {total_huerfanas:,}")
print(f"Prestamos inexistentes referenciados: {prestamos_inexistentes:,}")
print(f"Rango de prestamo_id: {min_id} - {max_id}")
print(f"Total pagado en cuotas huérfanas: ${total_pagado:,.2f}" if total_pagado else "Total pagado: $0.00")
print(f"Cuotas huérfanas con pagos: {cuotas_con_pagos:,}")

# Verificar si estos prestamo_id existen pero con otro estado
resultado = db.execute(text("""
    SELECT 
        COUNT(DISTINCT c.prestamo_id) AS prestamos_con_otro_estado
    FROM cuotas c
    LEFT JOIN prestamos p_aprobado ON c.prestamo_id = p_aprobado.id AND p_aprobado.estado = 'APROBADO'
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p_aprobado.id IS NULL
"""))

prestamos_otro_estado = resultado.scalar()
if prestamos_otro_estado > 0:
    print(f"\n⚠️ De estos prestamo_id, {prestamos_otro_estado} existen pero con estado diferente a APROBADO")

# ======================================================================
# 5. CONCILIACION: PRESTAMOS APROBADOS VS CUOTAS
# ======================================================================

print("\n5. CONCILIACION: PRESTAMOS APROBADOS VS CUOTAS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(DISTINCT p.id) AS prestamos_aprobados_con_cuotas,
        COUNT(DISTINCT c.prestamo_id) AS prestamos_con_cuotas_generadas,
        COUNT(c.id) AS total_cuotas_generadas,
        COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.prestamo_id END) AS prestamos_con_pagos
    FROM prestamos p
    INNER JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
"""))

row = resultado.fetchone()
prestamos_con_cuotas, prestamos_con_cuotas_gen, total_cuotas, prestamos_con_pagos = row

print(f"Préstamos aprobados CON cuotas: {prestamos_con_cuotas:,}")
print(f"Préstamos con cuotas generadas: {prestamos_con_cuotas_gen:,}")
print(f"Total cuotas generadas: {total_cuotas:,}")
print(f"Préstamos con pagos registrados: {prestamos_con_pagos:,}")

# Comparar con total de aprobados
diferencia = total_aprobados - prestamos_con_cuotas
if diferencia > 0:
    print(f"\n⚠️ Diferencia: {diferencia} préstamos aprobados NO tienen cuotas")
elif diferencia < 0:
    print(f"\n⚠️ Diferencia: {abs(diferencia)} préstamos con cuotas NO están aprobados")
else:
    print("\n✅ Todos los préstamos aprobados tienen cuotas")

# ======================================================================
# 6. VERIFICAR CONSISTENCIA: CUOTAS GENERADAS VS PLANIFICADAS
# ======================================================================

print("\n6. CONSISTENCIA: CUOTAS GENERADAS VS PLANIFICADAS:")
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
        COUNT(CASE WHEN cuotas_generadas > numero_cuotas THEN 1 END) AS prestamos_cuotas_extra
    FROM prestamos_cuotas
"""))

row = resultado.fetchone()
total_prestamos, prestamos_ok, prestamos_faltan, prestamos_extra = row

print(f"Total préstamos analizados: {total_prestamos:,}")
print(f"Préstamos con cuotas correctas: {prestamos_ok:,}")
print(f"Préstamos con cuotas faltantes: {prestamos_faltan:,}")
print(f"Préstamos con cuotas extra: {prestamos_extra:,}")

if prestamos_faltan > 0 or prestamos_extra > 0:
    print("\n⚠️ Hay inconsistencias en el número de cuotas")
else:
    print("\n✅ Todos los préstamos tienen el número correcto de cuotas")

# ======================================================================
# 7. RESUMEN DE CONCILIACION
# ======================================================================

print("\n7. RESUMEN DE CONCILIACION:")
print("-" * 70)

print(f"\n📊 PRESTAMOS APROBADOS:")
print(f"   Total: {total_aprobados:,}")
print(f"   Con cuotas: {prestamos_con_cuotas:,}")
print(f"   Sin cuotas: {diferencia if diferencia > 0 else 0:,}")

print(f"\n📊 CUOTAS:")
print(f"   Total generadas: {total_cuotas:,}")
print(f"   Huérfanas (sin préstamo aprobado): {total_huerfanas:,}")
print(f"   Con pagos registrados: {cuotas_con_pagos:,}")

print(f"\n📊 PRESTAMOS INEXISTENTES:")
print(f"   Referenciados por cuotas huérfanas: {prestamos_inexistentes:,}")
print(f"   Rango de IDs: {min_id} - {max_id}")

print(f"\n📊 CONSISTENCIA:")
print(f"   Préstamos con cuotas correctas: {prestamos_ok:,}")
print(f"   Préstamos con inconsistencias: {prestamos_faltan + prestamos_extra:,}")

# ======================================================================
# 8. RECOMENDACIONES
# ======================================================================

print("\n8. RECOMENDACIONES:")
print("-" * 70)

if total_huerfanas > 0:
    print(f"⚠️ Hay {total_huerfanas:,} cuotas huérfanas que referencian préstamos inexistentes")
    print(f"   - Estas cuotas tienen prestamo_id entre {min_id} y {max_id}")
    print(f"   - Los préstamos actuales tienen IDs entre {id_min} y {id_max}")
    if cuotas_con_pagos > 0:
        print(f"   - {cuotas_con_pagos:,} cuotas huérfanas tienen pagos registrados (${total_pagado:,.2f})")
        print("   - NO eliminar estas cuotas sin investigar más")

if diferencia > 0:
    print(f"\n⚠️ Hay {diferencia} préstamos aprobados sin cuotas generadas")
    print("   - Verificar por qué no tienen cuotas")
    print("   - Pueden requerir generación de tabla de amortización")

if prestamos_faltan > 0 or prestamos_extra > 0:
    print(f"\n⚠️ Hay {prestamos_faltan + prestamos_extra} préstamos con inconsistencias en cuotas")
    print("   - Verificar y corregir antes de restaurar préstamos")

if len(duplicados) > 0:
    print(f"\n⚠️ Hay {len(duplicados)} préstamos duplicados por ID")
    print("   - Investigar y eliminar duplicados antes de continuar")

print("\n✅ CONCLUSIÓN:")
print("   Antes de restaurar préstamos, verificar:")
print("   1. Si los préstamos 1-3784 fueron eliminados intencionalmente")
print("   2. Si hay información de clientes disponible para restaurar")
print("   3. Si las cuotas huérfanas deben mantenerse o eliminarse")
print("   4. Si hay duplicados que deben corregirse primero")

print("\n" + "=" * 70)

db.close()
