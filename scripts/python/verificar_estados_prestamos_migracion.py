"""Verificar que todos los préstamos estén en estado APROBADO después de migración"""
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
print("VERIFICACION: ESTADOS DE PRESTAMOS DESPUES DE MIGRACION")
print("=" * 70)
print("\nObjetivo: Verificar que todos los prestamos esten en estado 'APROBADO'")
print("Contexto: Migracion de base de datos")
print("\n" + "=" * 70)

# 1. Distribución de estados
print("\n1. DISTRIBUCION DE ESTADOS DE PRESTAMOS:")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            estado,
            COUNT(*) AS total_prestamos,
            COUNT(DISTINCT cedula) AS total_clientes_distintos,
            MIN(fecha_registro) AS primer_prestamo,
            MAX(fecha_registro) AS ultimo_prestamo,
            MIN(fecha_aprobacion) AS primera_aprobacion,
            MAX(fecha_aprobacion) AS ultima_aprobacion
        FROM prestamos
        GROUP BY estado
        ORDER BY total_prestamos DESC
    """)
)

distribucion = resultado.fetchall()
for estado, total, clientes, primer_prestamo, ultimo_prestamo, primera_aprob, ultima_aprob in distribucion:
    print(f"\n  Estado: {estado}")
    print(f"    Total prestamos: {total}")
    print(f"    Clientes distintos: {clientes}")
    print(f"    Primer prestamo: {primer_prestamo}")
    print(f"    Ultimo prestamo: {ultimo_prestamo}")
    if primera_aprob:
        print(f"    Primera aprobacion: {primera_aprob}")
        print(f"    Ultima aprobacion: {ultima_aprob}")

# 2. Préstamos que NO están aprobados
print("\n" + "=" * 70)
print("2. PRESTAMOS QUE NO ESTAN EN ESTADO 'APROBADO':")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            p.id AS prestamo_id,
            p.cedula,
            p.estado,
            p.total_financiamiento,
            p.numero_cuotas,
            p.fecha_registro,
            p.fecha_aprobacion,
            c.nombres AS nombre_cliente,
            c.estado AS estado_cliente,
            c.activo AS cliente_activo,
            COUNT(cu.id) AS total_cuotas_generadas
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado != 'APROBADO'
        GROUP BY p.id, p.cedula, p.estado, p.total_financiamiento, 
                 p.numero_cuotas, p.fecha_registro, p.fecha_aprobacion,
                 c.nombres, c.estado, c.activo
        ORDER BY p.estado, p.fecha_registro DESC
    """)
)

prestamos_no_aprobados = resultado.fetchall()

if len(prestamos_no_aprobados) == 0:
    print("\n[OK] Todos los prestamos estan en estado 'APROBADO'")
else:
    print(f"\n[ATENCION] Se encontraron {len(prestamos_no_aprobados)} prestamos NO aprobados:")
    for i, prestamo in enumerate(prestamos_no_aprobados[:20], 1):
        prestamo_id, cedula, estado, total_fin, num_cuotas, fecha_reg, fecha_aprob, nombre, estado_cliente, activo, cuotas = prestamo
        print(f"\n  Prestamo {i}:")
        print(f"    ID: {prestamo_id}")
        print(f"    Cedula: {cedula}")
        print(f"    Estado: {estado}")
        print(f"    Total financiamiento: ${total_fin:,.2f}")
        print(f"    Numero cuotas: {num_cuotas}")
        print(f"    Cuotas generadas: {cuotas}")
        if nombre:
            print(f"    Cliente: {nombre}")
            print(f"    Estado cliente: {estado_cliente}")
            print(f"    Cliente activo: {activo}")

# 3. Resumen ejecutivo
print("\n" + "=" * 70)
print("3. RESUMEN EJECUTIVO:")
print("-" * 70)

# Total préstamos
resultado = db.execute(text("SELECT COUNT(*) FROM prestamos"))
total_prestamos = resultado.scalar()

# Préstamos aprobados
resultado = db.execute(text("SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO'"))
prestamos_aprobados = resultado.scalar()

# Préstamos no aprobados
resultado = db.execute(text("SELECT COUNT(*) FROM prestamos WHERE estado != 'APROBADO'"))
prestamos_no_aprobados_count = resultado.scalar()

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
print(f"  Prestamos NO APROBADOS: {prestamos_no_aprobados_count}")
print(f"\nPrestamos aprobados:")
print(f"  Con cuotas generadas: {prestamos_aprobados_con_cuotas}")
print(f"  Sin cuotas generadas: {prestamos_aprobados_sin_cuotas}")

# 4. Verificación final
print("\n" + "=" * 70)
print("4. VERIFICACION FINAL:")
print("-" * 70)

if prestamos_no_aprobados_count == 0:
    print("\n[OK] VERIFICACION EXITOSA:")
    print("  Todos los prestamos estan en estado 'APROBADO'")
    print("  La migracion se completo correctamente")
else:
    print(f"\n[ATENCION] VERIFICACION CON PROBLEMAS:")
    print(f"  Hay {prestamos_no_aprobados_count} prestamos que NO estan en estado 'APROBADO'")
    print("  Se requiere revision manual o correccion")
    
    # Mostrar distribución de estados no aprobados
    resultado = db.execute(
        text("""
            SELECT estado, COUNT(*) 
            FROM prestamos 
            WHERE estado != 'APROBADO'
            GROUP BY estado
            ORDER BY COUNT(*) DESC
        """)
    )
    estados_no_aprobados = resultado.fetchall()
    print("\n  Distribucion de estados NO aprobados:")
    for estado, cantidad in estados_no_aprobados:
        print(f"    {estado}: {cantidad} prestamos")

print("\n" + "=" * 70)

db.close()
