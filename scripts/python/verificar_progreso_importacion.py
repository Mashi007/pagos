"""Verificar progreso de importación en tiempo real"""
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
    print("=" * 70)
    print("PROGRESO DE IMPORTACIÓN")
    print("=" * 70)
    
    # Verificar progreso
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS filas_importadas,
            ROUND(COUNT(*) * 100.0 / 4800.0, 1) AS porcentaje_completado,
            CASE 
                WHEN COUNT(*) = 0 THEN '⏳ Esperando inicio...'
                WHEN COUNT(*) < 4800 THEN CONCAT('⏳ En progreso: ', COUNT(*)::text, ' de 4,800 (', ROUND(COUNT(*) * 100.0 / 4800.0, 1)::text, '%)')
                WHEN COUNT(*) = 4800 THEN '✅ IMPORTACIÓN COMPLETA'
                ELSE CONCAT('⚠️ ', COUNT(*)::text, ' filas (más de lo esperado)')
            END AS estado
        FROM tabla_comparacion_externa
    """))
    
    row = resultado.fetchone()
    filas, porcentaje, estado = row
    
    print(f"Filas importadas: {filas:,}")
    print(f"Porcentaje completado: {porcentaje}%")
    print(f"Faltan: {4800 - filas:,} filas")
    print(f"Estado: {estado}")
    print("=" * 70)
    
    # Verificación adicional si hay datos
    if filas > 0:
        print("")
        print("VERIFICACIÓN ADICIONAL:")
        resultado2 = db.execute(text("""
            SELECT 
                COUNT(*) AS total_filas,
                COUNT(DISTINCT cedula) AS cedulas_unicas,
                MAX(abonos) AS max_abonos,
                SUM(abonos) AS total_abonos_sum
            FROM tabla_comparacion_externa
        """))
        
        row2 = resultado2.fetchone()
        total, cedulas, max_abonos, total_abonos = row2
        
        print(f"  Total filas: {total:,}")
        print(f"  Cédulas únicas: {cedulas:,}")
        print(f"  Máximo abonos: {max_abonos:,}" if max_abonos else "  Máximo abonos: NULL")
        print(f"  Total abonos: {total_abonos:,}" if total_abonos else "  Total abonos: NULL")
        
        if max_abonos and max_abonos > 999999999999.99:
            print("  ✅ Valores grandes manejados correctamente (sin overflow)")
    
    print("")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
