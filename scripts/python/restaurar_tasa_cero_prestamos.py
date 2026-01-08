"""Restaurar todos los préstamos a tasa 0% desde backup"""
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
print("RESTAURACION: TODOS LOS PRESTAMOS A TASA 0%")
print("=" * 70)

# 1. Verificar estado actual
print("\n1. ESTADO ACTUAL:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_prestamos,
        COUNT(CASE WHEN tasa_interes = 0.00 THEN 1 END) AS con_tasa_cero,
        COUNT(CASE WHEN tasa_interes != 0.00 THEN 1 END) AS con_otra_tasa
    FROM prestamos
"""))

row = resultado.fetchone()
total_prestamos, con_tasa_cero, con_otra_tasa = row

print(f"Total préstamos: {total_prestamos:,}")
print(f"Préstamos con tasa 0%: {con_tasa_cero:,}")
print(f"Préstamos con otra tasa: {con_otra_tasa:,}")

# 2. Verificar backup
print("\n2. VERIFICANDO BACKUP:")
print("-" * 70)

try:
    resultado = db.execute(text("SELECT COUNT(*) FROM prestamos_backup_tasa_interes"))
    total_backup = resultado.scalar()
    print(f"✅ Backup encontrado: {total_backup:,} préstamos")
except Exception as e:
    print(f"❌ No se encontró backup: {type(e).__name__}")
    print(f"   {str(e)}")
    db.close()
    sys.exit(1)

# 3. Restaurar todos los préstamos a tasa 0%
print("\n3. RESTAURANDO TODOS LOS PRESTAMOS A TASA 0%:")
print("-" * 70)

try:
    # Actualizar todos los préstamos a tasa 0%
    resultado = db.execute(text("""
        UPDATE prestamos
        SET tasa_interes = 0.00,
            fecha_actualizacion = CURRENT_TIMESTAMP
    """))
    
    db.commit()
    filas_actualizadas = resultado.rowcount
    print(f"✅ Actualizados: {filas_actualizadas:,} préstamos a tasa 0%")
    
    # Verificar restauración
    print("\n4. VERIFICANDO RESTAURACION:")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total_prestamos,
            COUNT(CASE WHEN tasa_interes = 0.00 THEN 1 END) AS con_tasa_cero,
            COUNT(CASE WHEN tasa_interes != 0.00 THEN 1 END) AS con_otra_tasa
        FROM prestamos
    """))
    
    row = resultado.fetchone()
    total_prestamos_final, con_tasa_cero_final, con_otra_tasa_final = row
    
    print(f"Total préstamos: {total_prestamos_final:,}")
    print(f"Préstamos con tasa 0%: {con_tasa_cero_final:,}")
    print(f"Préstamos con otra tasa: {con_otra_tasa_final:,}")
    
    if con_tasa_cero_final == total_prestamos_final and con_otra_tasa_final == 0:
        print("\n✅ CONFIRMADO: TODOS los préstamos tienen tasa 0%")
        print(f"   Total: {total_prestamos_final:,}")
        print(f"   Con tasa 0%: {con_tasa_cero_final:,} (100%)")
        print(f"   Con otra tasa: {con_otra_tasa_final:,} (0%)")
    else:
        print("\n⚠️ Verificar: Puede haber inconsistencias")
    
    # Distribución final
    print("\n5. DISTRIBUCION FINAL:")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT 
            tasa_interes,
            COUNT(*) AS cantidad
        FROM prestamos
        GROUP BY tasa_interes
        ORDER BY tasa_interes
    """))
    
    print(f"{'Tasa Interés':<15} {'Cantidad':<12}")
    print("-" * 30)
    for row in resultado.fetchall():
        tasa, cantidad = row
        print(f"{tasa:<15} {cantidad:<12}")
    
except Exception as e:
    db.rollback()
    print(f"\n❌ ERROR durante la restauración: {type(e).__name__}")
    print(f"   {str(e)}")
    print("\n   Se hizo rollback. Los datos no se modificaron.")
    sys.exit(1)

finally:
    db.close()

print("\n" + "=" * 70)
print("✅ RESTAURACION COMPLETADA")
print("=" * 70)
