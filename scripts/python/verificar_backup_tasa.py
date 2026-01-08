"""Verificar si existe backup de tasas de interés"""
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
print("VERIFICACION DE BACKUP DE TASAS")
print("=" * 70)

# Verificar si existe la tabla de backup
try:
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total_backup,
            MIN(fecha_backup) AS fecha_backup_min,
            MAX(fecha_backup) AS fecha_backup_max
        FROM prestamos_backup_tasa_interes
    """))
    
    row = resultado.fetchone()
    total_backup, fecha_min, fecha_max = row
    
    print(f"\n✅ Backup encontrado:")
    print(f"   Total préstamos en backup: {total_backup:,}")
    print(f"   Fecha del backup: {fecha_min}")
    
    # Verificar tasas en el backup
    resultado = db.execute(text("""
        SELECT 
            tasa_interes,
            COUNT(*) AS cantidad
        FROM prestamos_backup_tasa_interes
        GROUP BY tasa_interes
        ORDER BY tasa_interes
    """))
    
    print(f"\n   Tasas guardadas en backup:")
    for row in resultado.fetchall():
        tasa, cantidad = row
        print(f"     - Tasa {tasa}%: {cantidad:,} préstamos")
    
    print(f"\n   Puedes restaurar desde este backup si es necesario")
    
except Exception as e:
    print(f"\n❌ No se encontró tabla de backup: {type(e).__name__}")
    print(f"   {str(e)}")

print("\n" + "=" * 70)

db.close()
