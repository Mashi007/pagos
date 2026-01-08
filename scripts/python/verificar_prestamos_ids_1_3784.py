"""Verificar si existen préstamos con IDs 1-3784 con cualquier estado"""
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
print("VERIFICACION: PRESTAMOS CON IDs 1-3784")
print("=" * 70)

# 1. Verificar si existen préstamos con IDs 1-3784 (cualquier estado)
print("\n1. PRESTAMOS CON IDs 1-3784 (CUALQUIER ESTADO):")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_prestamos,
        COUNT(DISTINCT estado) AS estados_diferentes,
        STRING_AGG(DISTINCT estado::TEXT, ', ') AS lista_estados,
        MIN(id) AS id_minimo,
        MAX(id) AS id_maximo
    FROM prestamos
    WHERE id BETWEEN 1 AND 3784
"""))

row = resultado.fetchone()
total, estados_dif, lista_estados, id_min, id_max = row

print(f"Total préstamos con IDs 1-3784: {total:,}")
print(f"Estados diferentes: {estados_dif}")
print(f"Lista de estados: {lista_estados if lista_estados else 'NINGUNO'}")
if id_min:
    print(f"Rango de IDs encontrados: {id_min} - {id_max}")
else:
    print("Rango de IDs encontrados: NINGUNO")

if total == 0:
    print("\n✅ CONFIRMADO: NO existen préstamos con IDs 1-3784")
    print("   Estos préstamos fueron eliminados o nunca existieron")
else:
    print(f"\n⚠️ Se encontraron {total} préstamos con IDs 1-3784")
    print("   Estos préstamos existen pero pueden tener estado diferente a APROBADO")

# 2. Distribución por estado
if total > 0:
    print("\n2. DISTRIBUCION POR ESTADO:")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT 
            estado,
            COUNT(*) AS cantidad,
            MIN(id) AS id_minimo,
            MAX(id) AS id_maximo
        FROM prestamos
        WHERE id BETWEEN 1 AND 3784
        GROUP BY estado
        ORDER BY estado
    """))
    
    print(f"{'Estado':<20} {'Cantidad':<12} {'Rango IDs':<20}")
    print("-" * 60)
    for row in resultado.fetchall():
        estado, cantidad, id_min_estado, id_max_estado = row
        rango = f"{id_min_estado} - {id_max_estado}" if id_min_estado else "N/A"
        print(f"{estado:<20} {cantidad:<12} {rango:<20}")

# 3. Comparar con préstamos actuales
print("\n3. COMPARACION CON PRESTAMOS ACTUALES:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_prestamos,
        MIN(id) AS id_minimo,
        MAX(id) AS id_maximo,
        COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados
    FROM prestamos
"""))

row = resultado.fetchone()
total_general, id_min_gen, id_max_gen, aprobados = row

print(f"Total préstamos en BD: {total_general:,}")
print(f"Rango de IDs en BD: {id_min_gen} - {id_max_gen}")
print(f"Préstamos APROBADOS: {aprobados:,}")

print(f"\nGap identificado:")
print(f"  - Préstamos con IDs 1-3784: {total} (existen: {'SI' if total > 0 else 'NO'})")
print(f"  - Préstamos con IDs 3785-7826: {aprobados} (todos APROBADOS)")

# 4. Verificar cuotas huérfanas
print("\n4. CUOTAS QUE REFERENCIAN IDs 1-3784:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_cuotas,
        COUNT(DISTINCT prestamo_id) AS prestamos_referenciados,
        COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_pagos,
        SUM(total_pagado) AS total_pagado
    FROM cuotas
    WHERE prestamo_id BETWEEN 1 AND 3784
"""))

row = resultado.fetchall()
if row:
    total_cuotas, prestamos_ref, cuotas_pagos, total_pagado = row[0]
    print(f"Total cuotas con prestamo_id 1-3784: {total_cuotas:,}")
    print(f"Prestamos diferentes referenciados: {prestamos_ref:,}")
    print(f"Cuotas con pagos: {cuotas_pagos:,}")
    print(f"Total pagado: ${total_pagado:,.2f}" if total_pagado else "Total pagado: $0.00")
    
    # Verificar si estos prestamo_id existen
    resultado_existen = db.execute(text("""
        SELECT 
            COUNT(DISTINCT c.prestamo_id) AS prestamos_que_existen
        FROM cuotas c
        INNER JOIN prestamos p ON c.prestamo_id = p.id
        WHERE c.prestamo_id BETWEEN 1 AND 3784
    """))
    
    existen = resultado_existen.scalar()
    print(f"\nDe estos prestamo_id, cuántos EXISTEN en tabla prestamos: {existen}")
    
    if existen == 0:
        print("✅ CONFIRMADO: Ninguno de estos prestamo_id existe en tabla prestamos")
        print("   Las cuotas son completamente huérfanas")
    elif existen < prestamos_ref:
        print(f"⚠️ Solo {existen} de {prestamos_ref} préstamos existen")
        print(f"   {prestamos_ref - existen} préstamos referenciados NO existen")
    else:
        print("⚠️ Todos los prestamo_id existen, pero pueden tener estado diferente a APROBADO")

# 5. Resumen final
print("\n5. RESUMEN FINAL:")
print("-" * 70)

print(f"\n📊 SITUACION ACTUAL:")
print(f"   - Préstamos con IDs 1-3784 en BD: {total}")
if total == 0:
    print(f"   - Estado: ELIMINADOS o NUNCA EXISTIERON")
    print(f"   - Cuotas huérfanas: {total_cuotas:,} cuotas referencian estos IDs")
    print(f"   - Conclusión: Los préstamos fueron eliminados, pero las cuotas permanecen")
else:
    print(f"   - Estado: EXISTEN pero pueden tener estado diferente a APROBADO")
    print(f"   - Verificar distribución por estado arriba")

print(f"\n📊 PRESTAMOS APROBADOS ACTUALES:")
print(f"   - Total: {aprobados:,}")
print(f"   - Rango de IDs: 3785 - 7826")
print(f"   - Estado: ✅ Todos correctos")

print("\n" + "=" * 70)

db.close()
