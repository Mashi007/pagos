"""Verificacion rapida del avance de importacion"""
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

try:
    # Total de prestamos
    resultado = db.execute(text("SELECT COUNT(*) FROM prestamos"))
    total = resultado.scalar()
    print(f"Total prestamos importados: {total:,}")
    
    # Ultimos 5 prestamos
    resultado = db.execute(text("""
        SELECT id, cedula, nombres, fecha_requerimiento, fecha_aprobacion, estado
        FROM prestamos
        ORDER BY id DESC
        LIMIT 5
    """))
    
    print(f"\nUltimos 5 prestamos importados:")
    print("-" * 100)
    for row in resultado:
        print(f"  ID: {row.id} | Cedula: {row.cedula} | Fecha Req: {row.fecha_requerimiento} | Estado: {row.estado}")
    
    # Verificar fechas
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total,
            COUNT(CASE WHEN fecha_requerimiento IS NOT NULL THEN 1 END) AS con_fecha_req,
            COUNT(CASE WHEN fecha_aprobacion IS NOT NULL THEN 1 END) AS con_fecha_apr
        FROM prestamos
    """))
    row = resultado.fetchone()
    print(f"\nFechas importadas:")
    print(f"  Con fecha_requerimiento: {row.con_fecha_req:,} de {row.total:,}")
    print(f"  Con fecha_aprobacion: {row.con_fecha_apr:,} de {row.total:,}")
    
    # Clientes vinculados
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total,
            COUNT(cliente_id) AS con_cliente
        FROM prestamos
    """))
    row = resultado.fetchone()
    print(f"\nClientes vinculados:")
    print(f"  Con cliente_id: {row.con_cliente:,} de {row.total:,}")
    print(f"  Sin cliente_id: {row.total - row.con_cliente:,}")
    
finally:
    db.close()
