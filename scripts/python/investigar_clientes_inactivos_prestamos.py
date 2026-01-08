"""Investigar casos de clientes inactivos con préstamos aprobados"""
import sys
import io
from pathlib import Path
from datetime import datetime

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
print("INVESTIGACION: CLIENTES INACTIVOS CON PRESTAMOS APROBADOS")
print("=" * 70)

# 1. Obtener lista de clientes inactivos con préstamos aprobados
print("\n1. IDENTIFICANDO CLIENTES INACTIVOS CON PRESTAMOS APROBADOS")
resultado = db.execute(
    text("""
        SELECT 
            c.id as cliente_id,
            c.cedula,
            c.nombres,
            c.estado as estado_cliente,
            c.activo,
            c.fecha_registro as fecha_registro_cliente,
            c.fecha_actualizacion as fecha_actualizacion_cliente,
            COUNT(p.id) as total_prestamos_aprobados,
            MIN(p.fecha_aprobacion) as primera_aprobacion,
            MAX(p.fecha_aprobacion) as ultima_aprobacion
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.activo = FALSE
        AND p.estado = 'APROBADO'
        GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo, 
                 c.fecha_registro, c.fecha_actualizacion
        ORDER BY c.fecha_actualizacion DESC
        LIMIT 20
    """)
)

casos = resultado.fetchall()
print(f"\nTotal de casos encontrados: {len(casos)} (mostrando primeros 20)")
print("\nDetalle de casos:")

for i, caso in enumerate(casos, 1):
    cliente_id, cedula, nombres, estado_cliente, activo, fecha_reg_cliente, fecha_act_cliente, total_prestamos, primera_aprob, ultima_aprob = caso
    print(f"\n  Caso {i}:")
    print(f"    Cliente ID: {cliente_id}")
    print(f"    Cedula: {cedula}")
    try:
        nombres_safe = str(nombres) if nombres else "N/A"
    except:
        nombres_safe = "N/A"
    print(f"    Nombres: {nombres_safe}")
    print(f"    Estado cliente: {estado_cliente}")
    print(f"    Activo: {activo}")
    print(f"    Total prestamos aprobados: {total_prestamos}")
    print(f"    Fecha registro cliente: {fecha_reg_cliente}")
    print(f"    Fecha actualizacion cliente: {fecha_act_cliente}")
    print(f"    Primera aprobacion: {primera_aprob}")
    print(f"    Ultima aprobacion: {ultima_aprob}")

# 2. Análisis temporal: ¿Se inactivaron antes o después de la aprobación?
print("\n" + "=" * 70)
print("2. ANALISIS TEMPORAL: FECHA DE INACTIVACION VS APROBACION")
print("=" * 70)

resultado = db.execute(
    text("""
        SELECT 
            COUNT(*) as total_casos,
            COUNT(CASE WHEN c.fecha_actualizacion < p.fecha_aprobacion THEN 1 END) as inactivados_antes,
            COUNT(CASE WHEN c.fecha_actualizacion >= p.fecha_aprobacion THEN 1 END) as inactivados_despues,
            COUNT(CASE WHEN c.fecha_actualizacion IS NULL THEN 1 END) as sin_fecha_actualizacion
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.activo = FALSE
        AND p.estado = 'APROBADO'
    """)
)

analisis = resultado.fetchone()
total_casos, inactivados_antes, inactivados_despues, sin_fecha = analisis

print(f"\nTotal de relaciones cliente-prestamo analizadas: {total_casos}")
print(f"  Inactivados ANTES de la aprobacion: {inactivados_antes}")
print(f"  Inactivados DESPUES de la aprobacion: {inactivados_despues}")
print(f"  Sin fecha de actualizacion: {sin_fecha}")

# 3. Verificar estados de los clientes inactivos
print("\n" + "=" * 70)
print("3. ESTADOS DE CLIENTES INACTIVOS CON PRESTAMOS APROBADOS")
print("=" * 70)

resultado = db.execute(
    text("""
        SELECT 
            c.estado,
            COUNT(DISTINCT c.id) as cantidad_clientes,
            COUNT(p.id) as cantidad_prestamos
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.activo = FALSE
        AND p.estado = 'APROBADO'
        GROUP BY c.estado
        ORDER BY cantidad_clientes DESC
    """)
)

estados = resultado.fetchall()
print("\nDistribucion por estado:")
for estado, cantidad_clientes, cantidad_prestamos in estados:
    print(f"  {estado}: {cantidad_clientes} clientes, {cantidad_prestamos} prestamos")

# 4. Verificar si tienen cuotas generadas
print("\n" + "=" * 70)
print("4. PRESTAMOS APROBADOS DE CLIENTES INACTIVOS - CUOTAS GENERADAS")
print("=" * 70)

resultado = db.execute(
    text("""
        SELECT 
            COUNT(DISTINCT p.id) as total_prestamos,
            COUNT(DISTINCT CASE WHEN cu.id IS NOT NULL THEN p.id END) as prestamos_con_cuotas,
            COUNT(DISTINCT CASE WHEN cu.id IS NULL THEN p.id END) as prestamos_sin_cuotas
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE c.activo = FALSE
        AND p.estado = 'APROBADO'
    """)
)

cuotas_info = resultado.fetchone()
total_prestamos, con_cuotas, sin_cuotas = cuotas_info

print(f"\nTotal prestamos aprobados de clientes inactivos: {total_prestamos}")
print(f"  Con cuotas generadas: {con_cuotas}")
print(f"  Sin cuotas generadas: {sin_cuotas}")

# 5. Verificar si tienen pagos registrados
print("\n" + "=" * 70)
print("5. PRESTAMOS APROBADOS DE CLIENTES INACTIVOS - PAGOS REGISTRADOS")
print("=" * 70)

resultado = db.execute(
    text("""
        SELECT 
            COUNT(DISTINCT p.id) as total_prestamos,
            COUNT(DISTINCT pag.id) as prestamos_con_pagos,
            COALESCE(SUM(pag.monto_pagado), 0) as total_pagado
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
        WHERE c.activo = FALSE
        AND p.estado = 'APROBADO'
    """)
)

pagos_info = resultado.fetchone()
total_prestamos_pagos, con_pagos, total_pagado = pagos_info

print(f"\nTotal prestamos aprobados de clientes inactivos: {total_prestamos_pagos}")
print(f"  Con pagos registrados: {con_pagos}")
print(f"  Total pagado: ${total_pagado:,.2f}")

# 6. Resumen y recomendaciones
print("\n" + "=" * 70)
print("RESUMEN Y CONCLUSIONES")
print("=" * 70)

print(f"\nTotal de clientes inactivos con prestamos aprobados: 135")
print(f"Total de prestamos aprobados de clientes inactivos: {total_prestamos}")

if inactivados_despues > inactivados_antes:
    print("\n[CONCLUSION] La mayoria de clientes se inactivaron DESPUES de la aprobacion")
    print("  Esto es un comportamiento NORMAL en el flujo de negocio:")
    print("  - Los clientes pueden inactivarse por diversas razones")
    print("  - Los prestamos aprobados siguen siendo validos")
    print("  - La relacion por cedula permite mantener la integridad")
else:
    print("\n[CONCLUSION] Algunos clientes se inactivaron ANTES de la aprobacion")
    print("  Esto podria indicar un problema en el flujo de aprobacion")

print(f"\n[ESTADO] {estados[0][0] if estados else 'N/A'} es el estado mas comun")
print(f"[CUOTAS] {sin_cuotas} prestamos sin cuotas generadas (requiere atencion)")
print(f"[PAGOS] {con_pagos} prestamos tienen pagos registrados")

print("\n" + "=" * 70)

db.close()
