"""Script temporal para consultar estadísticas de clientes"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 60)
print("ESTADISTICAS DE CLIENTES")
print("=" * 60)

# Total de clientes
resultado = db.execute(text("SELECT COUNT(*) FROM clientes"))
total = resultado.scalar()
print(f"\nTotal de clientes: {total:,}")

# Clientes activos vs inactivos
resultado = db.execute(text("SELECT COUNT(*) FROM clientes WHERE activo = TRUE"))
activos = resultado.scalar()
resultado = db.execute(text("SELECT COUNT(*) FROM clientes WHERE activo = FALSE"))
inactivos = resultado.scalar()
print(f"\nClientes activos: {activos:,}")
print(f"Clientes inactivos: {inactivos:,}")
print(f"Porcentaje activos: {(activos/total*100):.1f}%")

# Clientes con préstamos
resultado = db.execute(text("SELECT COUNT(DISTINCT cliente_id) FROM prestamos"))
con_prestamos = resultado.scalar()
print(f"\nClientes con préstamos: {con_prestamos:,}")
print(f"Porcentaje con préstamos: {(con_prestamos/total*100):.1f}%")

# Clientes con pagos registrados (por cédula, ya que cliente_id puede estar NULL)
resultado = db.execute(
    text("SELECT COUNT(DISTINCT cedula) FROM pagos WHERE activo = TRUE")
)
con_pagos = resultado.scalar()
print(f"Clientes con pagos registrados (por cédula): {con_pagos:,}")
print(f"Porcentaje con pagos: {(con_pagos/total*100):.1f}%")

# Verificar pagos con cliente_id
resultado = db.execute(
    text("SELECT COUNT(*) FROM pagos WHERE activo = TRUE AND cliente_id IS NOT NULL")
)
pagos_con_cliente_id = resultado.scalar()
resultado = db.execute(text("SELECT COUNT(*) FROM pagos WHERE activo = TRUE"))
total_pagos = resultado.scalar()
print(f"\n[NOTA] Pagos con cliente_id asignado: {pagos_con_cliente_id:,} de {total_pagos:,} totales")

# Clientes sin préstamos
sin_prestamos = total - con_prestamos
print(f"\nClientes sin préstamos: {sin_prestamos:,}")

# Clientes con préstamos pero sin pagos
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT pr.cliente_id)
        FROM prestamos pr
        LEFT JOIN pagos p ON pr.cliente_id = p.cliente_id AND p.activo = TRUE
        WHERE p.id IS NULL
    """)
)
con_prestamos_sin_pagos = resultado.scalar()
print(f"Clientes con préstamos pero sin pagos: {con_prestamos_sin_pagos:,}")

print("=" * 60)

db.close()
