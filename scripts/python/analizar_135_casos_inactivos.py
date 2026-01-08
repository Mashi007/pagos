"""Analizar 135 casos de clientes inactivos con préstamos aprobados"""
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
print("ANALISIS: 135 CASOS DE CLIENTES INACTIVOS CON PRESTAMOS APROBADOS")
print("=" * 70)

# 1. Resumen general por estado
print("\n1. RESUMEN GENERAL POR ESTADO DEL CLIENTE:")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            c.estado AS estado_cliente,
            COUNT(DISTINCT c.id) AS total_clientes,
            COUNT(p.id) AS total_prestamos_aprobados,
            COUNT(DISTINCT CASE WHEN cu.id IS NOT NULL THEN p.id END) AS prestamos_con_cuotas,
            COUNT(DISTINCT CASE WHEN pag.id IS NOT NULL THEN p.id END) AS prestamos_con_pagos,
            COALESCE(SUM(pag.monto_pagado), 0) AS total_pagado
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
        WHERE c.activo = FALSE
          AND p.estado = 'APROBADO'
        GROUP BY c.estado
        ORDER BY total_clientes DESC
    """)
)

resumen_estados = resultado.fetchall()
for estado, total_clientes, total_prestamos, con_cuotas, con_pagos, total_pagado in resumen_estados:
    print(f"\n  Estado: {estado}")
    print(f"    Total clientes: {total_clientes}")
    print(f"    Total prestamos aprobados: {total_prestamos}")
    print(f"    Prestamos con cuotas: {con_cuotas}")
    print(f"    Prestamos con pagos: {con_pagos}")
    print(f"    Total pagado: ${total_pagado:,.2f}")

# 2. Clasificación: préstamos vigentes vs finalizados
print("\n" + "=" * 70)
print("2. CLASIFICACION: PRESTAMOS VIGENTES VS FINALIZADOS")
print("-" * 70)

resultado = db.execute(
    text("""
        WITH resumen_clientes AS (
            SELECT 
                c.id AS cliente_id,
                c.estado AS estado_actual,
                COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
                COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
                COALESCE(SUM(cu.total_pagado), 0) AS total_pagado,
                COUNT(p.id) AS total_prestamos
            FROM clientes c
            INNER JOIN prestamos p ON c.cedula = p.cedula
            LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
            WHERE c.activo = FALSE
              AND p.estado = 'APROBADO'
            GROUP BY c.id, c.estado
        )
        SELECT 
            CASE 
                WHEN capital_pendiente > 0 OR interes_pendiente > 0 
                THEN 'DEBE ESTAR ACTIVO (PRESTAMO VIGENTE)'
                WHEN total_pagado > 0 AND capital_pendiente = 0 AND interes_pendiente = 0
                THEN 'CORRECTO FINALIZADO (SALDO CERO)'
                ELSE 'SIN PAGOS (REVISAR)'
            END AS clasificacion,
            estado_actual,
            COUNT(*) AS total_clientes,
            SUM(total_prestamos) AS total_prestamos,
            SUM(capital_pendiente) AS total_capital_pendiente,
            SUM(interes_pendiente) AS total_interes_pendiente,
            SUM(total_pagado) AS total_pagado
        FROM resumen_clientes
        GROUP BY 
            CASE 
                WHEN capital_pendiente > 0 OR interes_pendiente > 0 
                THEN 'DEBE ESTAR ACTIVO (PRESTAMO VIGENTE)'
                WHEN total_pagado > 0 AND capital_pendiente = 0 AND interes_pendiente = 0
                THEN 'CORRECTO FINALIZADO (SALDO CERO)'
                ELSE 'SIN PAGOS (REVISAR)'
            END,
            estado_actual
        ORDER BY total_clientes DESC
    """)
)

clasificacion = resultado.fetchall()
for clasif, estado_actual, total_clientes, total_prestamos, capital_pend, interes_pend, total_pagado in clasificacion:
    print(f"\n  Clasificacion: {clasif}")
    print(f"    Estado actual: {estado_actual}")
    print(f"    Total clientes: {total_clientes}")
    print(f"    Total prestamos: {total_prestamos}")
    print(f"    Capital pendiente: ${capital_pend:,.2f}")
    print(f"    Interes pendiente: ${interes_pend:,.2f}")
    print(f"    Total pagado: ${total_pagado:,.2f}")

# 3. Clientes que deben estar ACTIVOS (tienen saldo pendiente)
print("\n" + "=" * 70)
print("3. CLIENTES QUE DEBEN ESTAR ACTIVOS (TIENEN SALDO PENDIENTE)")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            c.id AS cliente_id,
            c.cedula,
            c.nombres,
            c.estado AS estado_actual,
            c.activo,
            COUNT(p.id) AS total_prestamos_aprobados,
            COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
            COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
            COALESCE(SUM(cu.total_pagado), 0) AS total_pagado,
            COALESCE(SUM(cu.capital_pendiente), 0) + COALESCE(SUM(cu.interes_pendiente), 0) AS saldo_total_pendiente
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE c.activo = FALSE
          AND p.estado = 'APROBADO'
        GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
        HAVING COALESCE(SUM(cu.capital_pendiente), 0) > 0 
            OR COALESCE(SUM(cu.interes_pendiente), 0) > 0
        ORDER BY saldo_total_pendiente DESC
        LIMIT 20
    """)
)

clientes_activos = resultado.fetchall()
print(f"\nTotal clientes con saldo pendiente (mostrando primeros 20):")
for cliente_id, cedula, nombres, estado, activo, prestamos, capital_pend, interes_pend, total_pagado, saldo_total in clientes_activos:
    print(f"\n  Cliente ID: {cliente_id}")
    print(f"    Cedula: {cedula}")
    print(f"    Nombres: {nombres}")
    print(f"    Estado actual: {estado}")
    print(f"    Activo: {activo}")
    print(f"    Prestamos aprobados: {prestamos}")
    print(f"    Capital pendiente: ${capital_pend:,.2f}")
    print(f"    Interes pendiente: ${interes_pend:,.2f}")
    print(f"    Saldo total pendiente: ${saldo_total:,.2f}")
    print(f"    Total pagado: ${total_pagado:,.2f}")

# 4. Resumen ejecutivo
print("\n" + "=" * 70)
print("4. RESUMEN EJECUTIVO")
print("-" * 70)

# Total clientes inactivos con préstamos aprobados
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT c.id) 
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.activo = FALSE
          AND p.estado = 'APROBADO'
    """)
)
total_inactivos = resultado.scalar()

# Clientes INACTIVOS (estado)
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT c.id) 
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.estado = 'INACTIVO'
          AND p.estado = 'APROBADO'
    """)
)
total_estado_inactivo = resultado.scalar()

# Clientes FINALIZADOS
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT c.id) 
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.estado = 'FINALIZADO'
          AND p.estado = 'APROBADO'
    """)
)
total_finalizados = resultado.scalar()

# Clientes con saldo pendiente
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT c.id)
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE c.activo = FALSE
          AND p.estado = 'APROBADO'
        GROUP BY c.id
        HAVING COALESCE(SUM(cu.capital_pendiente), 0) > 0 
            OR COALESCE(SUM(cu.interes_pendiente), 0) > 0
    """)
)
total_con_saldo = len(resultado.fetchall())

# Clientes sin saldo pendiente
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT c.id)
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE c.activo = FALSE
          AND p.estado = 'APROBADO'
        GROUP BY c.id
        HAVING COALESCE(SUM(cu.capital_pendiente), 0) = 0 
            AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
            AND COALESCE(SUM(cu.total_pagado), 0) > 0
    """)
)
total_sin_saldo = len(resultado.fetchall())

print(f"\nTotal clientes inactivos (activo=FALSE) con prestamos aprobados: {total_inactivos}")
print(f"  - Estado INACTIVO: {total_estado_inactivo}")
print(f"  - Estado FINALIZADO: {total_finalizados}")
print(f"\nClasificacion por saldo:")
print(f"  - Con saldo pendiente (deben estar ACTIVOS): {total_con_saldo}")
print(f"  - Sin saldo pendiente (correctamente FINALIZADOS): {total_sin_saldo}")

print("\n" + "=" * 70)
print("CONCLUSIONES:")
print("=" * 70)
print(f"\n1. {total_estado_inactivo} clientes en estado INACTIVO requieren correccion")
print(f"2. {total_con_saldo} clientes tienen saldo pendiente y deben estar ACTIVOS")
print(f"3. {total_sin_saldo} clientes estan correctamente FINALIZADOS (sin saldo)")
print(f"\nACCION REQUERIDA:")
print(f"  - Generar script SQL para cambiar a ACTIVO los clientes con saldo pendiente")

print("\n" + "=" * 70)

db.close()
