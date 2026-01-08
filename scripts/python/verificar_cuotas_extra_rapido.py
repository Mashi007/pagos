"""Verificación rápida de cuotas extra"""
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Verificar préstamos con cuotas extra
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT p.id)
        FROM prestamos p
        INNER JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.numero_cuotas
        HAVING COUNT(cu.id) > p.numero_cuotas
    """)
)

prestamos_extra = len(resultado.fetchall())
print(f"Prestamos con cuotas extra: {prestamos_extra}")

# Verificar préstamos con cuotas faltantes
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT p.id)
        FROM prestamos p
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.numero_cuotas
        HAVING COUNT(cu.id) < p.numero_cuotas
    """)
)

prestamos_faltantes = len(resultado.fetchall())
print(f"Prestamos con cuotas faltantes: {prestamos_faltantes}")

db.close()
