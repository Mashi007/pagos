"""Verificar que clientes INACTIVOS (pasivos) no tengan préstamos aprobados"""
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
print("VERIFICACION: CLIENTES INACTIVOS (PASIVOS) VS PRESTAMOS")
print("=" * 70)
print("\nRegla de negocio:")
print("  - Clientes INACTIVOS (pasivos) = No concretaron opcion de prestamos")
print("  - Deben mantenerse en tabla clientes pero SIN prestamos aprobados")
print("  - Clientes FINALIZADOS = Completaron su ciclo, pueden tener prestamos aprobados")
print("\n" + "=" * 70)

# 1. Verificar clientes en estado INACTIVO con préstamos aprobados
print("\n1. CLIENTES EN ESTADO 'INACTIVO' CON PRESTAMOS APROBADOS")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            c.id as cliente_id,
            c.cedula,
            c.nombres,
            c.estado,
            c.activo,
            COUNT(p.id) as total_prestamos_aprobados
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.estado = 'INACTIVO'
        AND p.estado = 'APROBADO'
        GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
        ORDER BY total_prestamos_aprobados DESC
    """)
)

clientes_inactivos_con_prestamos = resultado.fetchall()

if len(clientes_inactivos_con_prestamos) == 0:
    print("\n[OK] No hay clientes en estado INACTIVO con prestamos aprobados")
    print("     La regla de negocio se cumple correctamente")
else:
    print(f"\n[PROBLEMA] Se encontraron {len(clientes_inactivos_con_prestamos)} clientes INACTIVOS con prestamos aprobados:")
    for i, caso in enumerate(clientes_inactivos_con_prestamos, 1):
        cliente_id, cedula, nombres, estado, activo, total_prestamos = caso
        print(f"\n  Caso {i}:")
        print(f"    Cliente ID: {cliente_id}")
        print(f"    Cedula: {cedula}")
        print(f"    Nombres: {nombres}")
        print(f"    Estado: {estado}")
        print(f"    Activo: {activo}")
        print(f"    Prestamos aprobados: {total_prestamos}")

# 2. Verificar distribución de estados de clientes
print("\n" + "=" * 70)
print("2. DISTRIBUCION DE ESTADOS DE CLIENTES")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            estado,
            activo,
            COUNT(*) as cantidad,
            COUNT(CASE WHEN EXISTS (
                SELECT 1 FROM prestamos p 
                WHERE p.cedula = c.cedula AND p.estado = 'APROBADO'
            ) THEN 1 END) as con_prestamos_aprobados
        FROM clientes c
        GROUP BY estado, activo
        ORDER BY estado, activo
    """)
)

distribucion = resultado.fetchall()
print("\nDistribucion:")
for estado, activo, cantidad, con_prestamos in distribucion:
    print(f"  Estado: {estado}, Activo: {activo}")
    print(f"    Total clientes: {cantidad}")
    print(f"    Con prestamos aprobados: {con_prestamos}")
    print(f"    Sin prestamos aprobados: {cantidad - con_prestamos}")

# 3. Verificar clientes INACTIVOS sin préstamos (comportamiento esperado)
print("\n" + "=" * 70)
print("3. CLIENTES INACTIVOS SIN PRESTAMOS (COMPORTAMIENTO ESPERADO)")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT COUNT(*) 
        FROM clientes c
        WHERE c.estado = 'INACTIVO'
        AND NOT EXISTS (
            SELECT 1 FROM prestamos p 
            WHERE p.cedula = c.cedula AND p.estado = 'APROBADO'
        )
    """)
)
inactivos_sin_prestamos = resultado.scalar()

resultado = db.execute(
    text("SELECT COUNT(*) FROM clientes WHERE estado = 'INACTIVO'")
)
total_inactivos = resultado.scalar()

print(f"\nTotal clientes INACTIVOS: {total_inactivos}")
print(f"  Sin prestamos aprobados (esperado): {inactivos_sin_prestamos}")
print(f"  Con prestamos aprobados (problema): {total_inactivos - inactivos_sin_prestamos}")

# 4. Verificar clientes FINALIZADOS (comportamiento esperado)
print("\n" + "=" * 70)
print("4. CLIENTES FINALIZADOS (COMPORTAMIENTO ESPERADO)")
print("-" * 70)

resultado = db.execute(
    text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN EXISTS (
                SELECT 1 FROM prestamos p 
                WHERE p.cedula = c.cedula AND p.estado = 'APROBADO'
            ) THEN 1 END) as con_prestamos_aprobados
        FROM clientes c
        WHERE c.estado = 'FINALIZADO'
    """)
)
finalizados_info = resultado.fetchone()
total_finalizados, finalizados_con_prestamos = finalizados_info

print(f"\nTotal clientes FINALIZADOS: {total_finalizados}")
print(f"  Con prestamos aprobados (esperado): {finalizados_con_prestamos}")
print(f"  Sin prestamos aprobados: {total_finalizados - finalizados_con_prestamos}")

# 5. Resumen y conclusiones
print("\n" + "=" * 70)
print("RESUMEN Y CONCLUSIONES")
print("=" * 70)

if len(clientes_inactivos_con_prestamos) == 0:
    print("\n[OK] REGLA DE NEGOCIO CONFIRMADA:")
    print("  - Clientes INACTIVOS (pasivos) NO tienen prestamos aprobados")
    print("  - Clientes FINALIZADOS pueden tener prestamos aprobados (completaron ciclo)")
    print("  - La relacion por cedula funciona correctamente")
else:
    print(f"\n[PROBLEMA] REGLA DE NEGOCIO NO SE CUMPLE:")
    print(f"  - {len(clientes_inactivos_con_prestamos)} clientes INACTIVOS tienen prestamos aprobados")
    print("  - Estos clientes deberian estar en otro estado o no tener prestamos aprobados")
    print("\n  ACCION REQUERIDA:")
    print("  - Revisar estos casos y corregir el estado o los prestamos")

print("\n" + "=" * 70)

db.close()
