"""Verificar regla de negocio: Clientes activos tienen préstamos aprobados"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 70)
print("VERIFICACION DE REGLA DE NEGOCIO")
print("=" * 70)
print("\nRegla a verificar:")
print("1. Todos los clientes ACTIVOS tienen préstamos en estado APROBADO")
print("2. Solo los clientes ACTIVOS tienen préstamos APROBADOS")
print("3. Se relacionan por número de cédula")
print("\n" + "=" * 70)

# 1. Verificar que todos los clientes activos tienen préstamos aprobados
print("\n1. VERIFICANDO: Todos los clientes activos tienen préstamos APROBADOS")
resultado = db.execute(
    text("""
        SELECT COUNT(*) 
        FROM clientes c
        WHERE c.activo = TRUE
        AND NOT EXISTS (
            SELECT 1 
            FROM prestamos p 
            WHERE p.cedula = c.cedula 
            AND p.estado = 'APROBADO'
        )
    """)
)
clientes_activos_sin_prestamo_aprobado = resultado.scalar()
print(f"   Clientes activos SIN préstamo aprobado: {clientes_activos_sin_prestamo_aprobado}")

if clientes_activos_sin_prestamo_aprobado == 0:
    print("   [OK] CONFIRMADO: Todos los clientes activos tienen prestamos APROBADOS")
else:
    print(f"   [PROBLEMA] {clientes_activos_sin_prestamo_aprobado} clientes activos sin prestamo aprobado")

# 2. Verificar que solo los clientes activos tienen préstamos aprobados
print("\n2. VERIFICANDO: Solo los clientes ACTIVOS tienen préstamos APROBADOS")
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT p.cedula)
        FROM prestamos p
        WHERE p.estado = 'APROBADO'
        AND NOT EXISTS (
            SELECT 1 
            FROM clientes c 
            WHERE c.cedula = p.cedula 
            AND c.activo = TRUE
        )
    """)
)
prestamos_aprobados_clientes_inactivos = resultado.scalar()
print(f"   Préstamos APROBADOS de clientes INACTIVOS: {prestamos_aprobados_clientes_inactivos}")

if prestamos_aprobados_clientes_inactivos == 0:
    print("   [OK] CONFIRMADO: Solo los clientes activos tienen prestamos APROBADOS")
else:
    print(f"   [PROBLEMA] {prestamos_aprobados_clientes_inactivos} prestamos aprobados de clientes inactivos")

# 3. Verificar relación por cédula
print("\n3. VERIFICANDO: Relación por número de cédula")
resultado = db.execute(
    text("""
        SELECT COUNT(*) 
        FROM prestamos p
        WHERE p.estado = 'APROBADO'
        AND NOT EXISTS (
            SELECT 1 
            FROM clientes c 
            WHERE c.cedula = p.cedula
        )
    """)
)
prestamos_aprobados_sin_cliente = resultado.scalar()
print(f"   Préstamos APROBADOS con cédula que NO existe en clientes: {prestamos_aprobados_sin_cliente}")

if prestamos_aprobados_sin_cliente == 0:
    print("   [OK] CONFIRMADO: Todos los prestamos APROBADOS tienen cedula valida en clientes")
else:
    print(f"   [PROBLEMA] {prestamos_aprobados_sin_cliente} prestamos aprobados con cedula invalida")

# Estadísticas adicionales
print("\n" + "=" * 70)
print("ESTADISTICAS ADICIONALES")
print("=" * 70)

# Total de clientes activos
resultado = db.execute(text("SELECT COUNT(*) FROM clientes WHERE activo = TRUE"))
total_activos = resultado.scalar()
print(f"\nTotal clientes activos: {total_activos:,}")

# Total de préstamos aprobados
resultado = db.execute(text("SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO'"))
total_aprobados = resultado.scalar()
print(f"Total préstamos APROBADOS: {total_aprobados:,}")

# Clientes activos con préstamos aprobados
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT c.id)
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.activo = TRUE AND p.estado = 'APROBADO'
    """)
)
activos_con_aprobados = resultado.scalar()
print(f"Clientes activos con préstamos APROBADOS: {activos_con_aprobados:,}")

# Verificar si hay clientes inactivos con préstamos aprobados
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT c.id)
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.activo = FALSE AND p.estado = 'APROBADO'
    """)
)
inactivos_con_aprobados = resultado.scalar()
print(f"Clientes INACTIVOS con préstamos APROBADOS: {inactivos_con_aprobados:,}")

# Verificar si hay clientes activos con préstamos en otros estados
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT c.id)
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.activo = TRUE AND p.estado != 'APROBADO'
    """)
)
activos_con_otros_estados = resultado.scalar()
print(f"Clientes activos con préstamos en otros estados (no APROBADO): {activos_con_otros_estados:,}")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)

if (clientes_activos_sin_prestamo_aprobado == 0 and 
    prestamos_aprobados_clientes_inactivos == 0 and 
    prestamos_aprobados_sin_cliente == 0):
    print("\n[OK] REGLA CONFIRMADA:")
    print("   - Todos los clientes ACTIVOS tienen prestamos APROBADOS")
    print("   - Solo los clientes ACTIVOS tienen prestamos APROBADOS")
    print("   - La relacion se hace por numero de cedula")
else:
    print("\n[PROBLEMA] REGLA NO SE CUMPLE COMPLETAMENTE:")
    if clientes_activos_sin_prestamo_aprobado > 0:
        print(f"   - {clientes_activos_sin_prestamo_aprobado} clientes activos sin préstamo aprobado")
    if prestamos_aprobados_clientes_inactivos > 0:
        print(f"   - {prestamos_aprobados_clientes_inactivos} préstamos aprobados de clientes inactivos")
    if prestamos_aprobados_sin_cliente > 0:
        print(f"   - {prestamos_aprobados_sin_cliente} préstamos aprobados con cédula inválida")

print("=" * 70)

db.close()
