"""Investigar inconsistencias en cuotas de préstamos"""
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
print("INVESTIGACION: INCONSISTENCIAS EN CUOTAS DE PRESTAMOS")
print("=" * 70)
print("\nObjetivo: Investigar prestamos con cuotas de mas o cuotas faltantes")
print("\n" + "=" * 70)

# 1. Préstamos con cuotas de más
print("\n1. PRESTAMOS CON CUOTAS DE MAS:")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            p.id AS prestamo_id,
            p.cedula,
            c.nombres AS nombre_cliente,
            p.numero_cuotas AS cuotas_planificadas,
            COUNT(cu.id) AS cuotas_generadas,
            COUNT(cu.id) - p.numero_cuotas AS cuotas_extra,
            ROUND((COUNT(cu.id)::numeric / p.numero_cuotas::numeric), 2) AS multiplicador,
            p.total_financiamiento,
            p.cuota_periodo,
            p.modalidad_pago,
            p.fecha_aprobacion,
            COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
            COUNT(CASE WHEN cu.estado != 'PAGADO' THEN 1 END) AS cuotas_pendientes
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula
        INNER JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, p.total_financiamiento,
                 p.cuota_periodo, p.modalidad_pago, p.fecha_aprobacion
        HAVING COUNT(cu.id) > p.numero_cuotas
        ORDER BY (COUNT(cu.id) - p.numero_cuotas) DESC, p.id
    """)
)

prestamos_cuotas_extra = resultado.fetchall()

if len(prestamos_cuotas_extra) == 0:
    print("\n[OK] No hay prestamos con cuotas de mas")
else:
    print(f"\n[ATENCION] Se encontraron {len(prestamos_cuotas_extra)} prestamos con cuotas de mas:")
    for i, prestamo in enumerate(prestamos_cuotas_extra, 1):
        prestamo_id, cedula, nombre, planificadas, generadas, extra, multiplicador, total_fin, cuota_periodo, modalidad, fecha_aprob, pagadas, pendientes = prestamo
        print(f"\n  Prestamo {i}:")
        print(f"    ID: {prestamo_id}")
        print(f"    Cedula: {cedula}")
        if nombre:
            print(f"    Cliente: {nombre}")
        print(f"    Cuotas planificadas: {planificadas}")
        print(f"    Cuotas generadas: {generadas}")
        print(f"    Cuotas extra: {extra}")
        print(f"    Multiplicador: {multiplicador}x (parece regenerado {int(multiplicador)} veces)")
        print(f"    Modalidad: {modalidad}")
        print(f"    Fecha aprobacion: {fecha_aprob}")
        print(f"    Cuotas pagadas: {pagadas}")
        print(f"    Cuotas pendientes: {pendientes}")

# 2. Verificar cuotas duplicadas
print("\n" + "=" * 70)
print("2. VERIFICAR CUOTAS DUPLICADAS (MISMO numero_cuota):")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            p.id AS prestamo_id,
            p.cedula,
            c.nombres AS nombre_cliente,
            cu.numero_cuota,
            COUNT(*) AS veces_duplicada,
            STRING_AGG(cu.id::text, ', ' ORDER BY cu.id) AS ids_cuotas
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula
        INNER JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.cedula, c.nombres, cu.numero_cuota
        HAVING COUNT(*) > 1
        ORDER BY p.id, cu.numero_cuota
    """)
)

cuotas_duplicadas = resultado.fetchall()

if len(cuotas_duplicadas) == 0:
    print("\n[OK] No hay cuotas duplicadas (mismo numero_cuota)")
else:
    print(f"\n[ATENCION] Se encontraron cuotas duplicadas en {len(set(c[0] for c in cuotas_duplicadas))} prestamos:")
    for i, dup in enumerate(cuotas_duplicadas[:20], 1):
        prestamo_id, cedula, nombre, numero_cuota, veces, ids = dup
        print(f"\n  Duplicado {i}:")
        print(f"    Prestamo ID: {prestamo_id}")
        print(f"    Cedula: {cedula}")
        if nombre:
            print(f"    Cliente: {nombre}")
        print(f"    Numero cuota: {numero_cuota}")
        print(f"    Veces duplicada: {veces}")
        print(f"    IDs de cuotas: {ids}")

# 3. Préstamos con cuotas faltantes
print("\n" + "=" * 70)
print("3. PRESTAMOS CON CUOTAS FALTANTES:")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            p.id AS prestamo_id,
            p.cedula,
            c.nombres AS nombre_cliente,
            p.numero_cuotas AS cuotas_planificadas,
            COUNT(cu.id) AS cuotas_generadas,
            p.numero_cuotas - COUNT(cu.id) AS cuotas_faltantes,
            ROUND((COUNT(cu.id)::numeric / p.numero_cuotas::numeric) * 100, 2) AS porcentaje_generado,
            p.total_financiamiento,
            p.cuota_periodo,
            p.modalidad_pago,
            p.fecha_aprobacion,
            COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, p.total_financiamiento,
                 p.cuota_periodo, p.modalidad_pago, p.fecha_aprobacion
        HAVING COUNT(cu.id) < p.numero_cuotas
        ORDER BY (p.numero_cuotas - COUNT(cu.id)) DESC, p.id
    """)
)

prestamos_cuotas_faltantes = resultado.fetchall()

if len(prestamos_cuotas_faltantes) == 0:
    print("\n[OK] No hay prestamos con cuotas faltantes")
else:
    print(f"\n[ATENCION] Se encontraron {len(prestamos_cuotas_faltantes)} prestamos con cuotas faltantes:")
    for i, prestamo in enumerate(prestamos_cuotas_faltantes, 1):
        prestamo_id, cedula, nombre, planificadas, generadas, faltantes, porcentaje, total_fin, cuota_periodo, modalidad, fecha_aprob, pagadas = prestamo
        print(f"\n  Prestamo {i}:")
        print(f"    ID: {prestamo_id}")
        print(f"    Cedula: {cedula}")
        if nombre:
            print(f"    Cliente: {nombre}")
        print(f"    Cuotas planificadas: {planificadas}")
        print(f"    Cuotas generadas: {generadas}")
        print(f"    Cuotas faltantes: {faltantes}")
        print(f"    Porcentaje generado: {porcentaje}%")
        print(f"    Modalidad: {modalidad}")
        print(f"    Fecha aprobacion: {fecha_aprob}")
        print(f"    Cuotas pagadas: {pagadas}")

# 4. Análisis temporal: fechas de generación
print("\n" + "=" * 70)
print("4. ANALISIS TEMPORAL: FECHAS DE GENERACION:")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            p.id AS prestamo_id,
            p.cedula,
            c.nombres AS nombre_cliente,
            p.numero_cuotas AS cuotas_planificadas,
            COUNT(cu.id) AS cuotas_generadas,
            MIN(cu.fecha_vencimiento) AS primera_cuota_vencimiento,
            MAX(cu.fecha_vencimiento) AS ultima_cuota_vencimiento,
            COUNT(DISTINCT DATE(cu.fecha_vencimiento)) AS fechas_vencimiento_distintas,
            CASE 
                WHEN COUNT(DISTINCT DATE(cu.fecha_vencimiento)) > 1 THEN 'MULTIPLES FECHAS VENCIMIENTO'
                ELSE 'FECHA VENCIMIENTO UNICA'
            END AS patron_generacion
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula
        INNER JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
          AND p.id IN (
              SELECT p2.id
              FROM prestamos p2
              INNER JOIN cuotas cu2 ON p2.id = cu2.prestamo_id
              WHERE p2.estado = 'APROBADO'
              GROUP BY p2.id, p2.numero_cuotas
              HAVING COUNT(cu2.id) != p2.numero_cuotas
          )
        GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas
        ORDER BY COUNT(DISTINCT DATE(cu.fecha_registro)) DESC, p.id
        LIMIT 20
    """)
)

analisis_temporal = resultado.fetchall()

if len(analisis_temporal) > 0:
    print(f"\nAnalisis de {len(analisis_temporal)} prestamos con inconsistencias:")
    for i, analisis in enumerate(analisis_temporal, 1):
        prestamo_id, cedula, nombre, planificadas, generadas, primera, ultima, dias_distintos, patron = analisis
        print(f"\n  Prestamo {i}:")
        print(f"    ID: {prestamo_id}")
        print(f"    Cedula: {cedula}")
        if nombre:
            print(f"    Cliente: {nombre}")
        print(f"    Cuotas planificadas: {planificadas}, Generadas: {generadas}")
        print(f"    Primera cuota registrada: {primera}")
        print(f"    Ultima cuota registrada: {ultima}")
        print(f"    Dias distintos de generacion: {dias_distintos}")
        print(f"    Patron: {patron}")

# 5. Resumen de inconsistencias
print("\n" + "=" * 70)
print("5. RESUMEN DE INCONSISTENCIAS:")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            CASE 
                WHEN COUNT(cu.id) > p.numero_cuotas THEN 'CUOTAS DE MAS'
                WHEN COUNT(cu.id) < p.numero_cuotas THEN 'CUOTAS FALTANTES'
                ELSE 'OK'
            END AS tipo_inconsistencia,
            COUNT(DISTINCT p.id) AS total_prestamos,
            SUM(COUNT(cu.id) - p.numero_cuotas) AS diferencia_total_cuotas,
            ROUND(AVG(COUNT(cu.id) - p.numero_cuotas), 2) AS diferencia_promedio,
            MIN(COUNT(cu.id) - p.numero_cuotas) AS diferencia_minima,
            MAX(COUNT(cu.id) - p.numero_cuotas) AS diferencia_maxima
        FROM prestamos p
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.numero_cuotas
        HAVING COUNT(cu.id) != p.numero_cuotas
        GROUP BY tipo_inconsistencia
        ORDER BY total_prestamos DESC
    """)
)

resumen = resultado.fetchall()

if len(resumen) > 0:
    print("\nResumen por tipo de inconsistencia:")
    for tipo, total, diff_total, diff_promedio, diff_min, diff_max in resumen:
        print(f"\n  {tipo}:")
        print(f"    Total prestamos afectados: {total}")
        print(f"    Diferencia total de cuotas: {diff_total}")
        print(f"    Diferencia promedio: {diff_promedio}")
        print(f"    Diferencia minima: {diff_min}")
        print(f"    Diferencia maxima: {diff_max}")

# 6. Conclusiones
print("\n" + "=" * 70)
print("6. CONCLUSIONES:")
print("-" * 70)

total_inconsistencias = len(prestamos_cuotas_extra) + len(prestamos_cuotas_faltantes)
total_duplicados = len(set(c[0] for c in cuotas_duplicadas)) if len(cuotas_duplicadas) > 0 else 0

print(f"\nTotal prestamos con inconsistencias: {total_inconsistencias}")
print(f"  - Con cuotas de mas: {len(prestamos_cuotas_extra)}")
print(f"  - Con cuotas faltantes: {len(prestamos_cuotas_faltantes)}")
print(f"  - Con cuotas duplicadas: {total_duplicados}")

if total_inconsistencias > 0:
    print("\n[RECOMENDACIONES]:")
    print("  1. Revisar prestamos con cuotas de mas: posible regeneracion multiple")
    print("  2. Revisar prestamos con cuotas faltantes: posible generacion incompleta")
    print("  3. Si hay duplicados: considerar limpieza de cuotas duplicadas")
    print("  4. Regenerar cuotas faltantes usando el servicio de amortizacion")

print("\n" + "=" * 70)

db.close()
