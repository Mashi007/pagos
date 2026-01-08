"""Actualizar tasa de interés de préstamos con tasa 0%"""
import sys
import io
from pathlib import Path
from decimal import Decimal

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
print("ACTUALIZACION DE TASA DE INTERES")
print("=" * 70)

# Verificar préstamos con tasa 0%
print("\n1. VERIFICANDO PRESTAMOS CON TASA 0%:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_prestamos_tasa_cero,
        COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados
    FROM prestamos
    WHERE tasa_interes = 0.00
"""))

row = resultado.fetchone()
total_tasa_cero, aprobados = row

print(f"Total préstamos con tasa 0%: {total_tasa_cero:,}")
print(f"Préstamos APROBADOS con tasa 0%: {aprobados:,}")

if total_tasa_cero == 0:
    print("\n✅ No hay préstamos con tasa 0% para actualizar")
    db.close()
    sys.exit(0)

# Solicitar nueva tasa
print("\n2. ESPECIFICAR NUEVA TASA DE INTERES:")
print("-" * 70)
print("⚠️ IMPORTANTE: Especifica la nueva tasa de interés anual (%)")
print("   Ejemplo: 12.00 para 12%, 15.50 para 15.5%")
print("\n   NOTA: Este script actualizará TODOS los préstamos con tasa 0%")
print("   Las cuotas existentes NO se recalcularán automáticamente")

# Para ejecución no interactiva, usar valor por defecto o variable de entorno
# En producción, esto debería venir de parámetro o configuración
nueva_tasa = 12.00  # ⚠️ VALOR POR DEFECTO - Cambiar según necesites

print(f"\n   Nueva tasa de interés: {nueva_tasa}%")
print(f"   Préstamos a actualizar: {total_tasa_cero:,}")

# Confirmar
print("\n3. CONFIRMACION:")
print("-" * 70)
print(f"¿Actualizar {total_tasa_cero:,} préstamos de tasa 0% a {nueva_tasa}%?")
print("⚠️ Esta acción actualizará la tasa en la tabla prestamos")
print("   Las cuotas existentes mantendrán sus montos actuales")
print("   (No se recalcularán automáticamente)")

# Crear backup
print("\n4. CREANDO BACKUP...")
print("-" * 70)

try:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS prestamos_backup_tasa_interes AS
        SELECT 
            id,
            tasa_interes,
            CURRENT_TIMESTAMP AS fecha_backup
        FROM prestamos
        WHERE tasa_interes = 0.00
    """))
    db.commit()
    
    resultado = db.execute(text("SELECT COUNT(*) FROM prestamos_backup_tasa_interes"))
    total_backup = resultado.scalar()
    print(f"✅ Backup creado: {total_backup:,} préstamos guardados")
    
    # Actualizar tasa
    print("\n5. ACTUALIZANDO TASA DE INTERES...")
    print("-" * 70)
    
    resultado = db.execute(text("""
        UPDATE prestamos
        SET tasa_interes = :nueva_tasa,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE tasa_interes = 0.00
    """), {"nueva_tasa": Decimal(str(nueva_tasa))})
    
    db.commit()
    filas_actualizadas = resultado.rowcount
    print(f"✅ Actualizados: {filas_actualizadas:,} préstamos")
    print(f"   Nueva tasa: {nueva_tasa}%")
    
    # Verificar actualización
    print("\n6. VERIFICANDO ACTUALIZACION...")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total_prestamos_tasa_cero,
            COUNT(CASE WHEN tasa_interes = :nueva_tasa THEN 1 END) AS prestamos_con_nueva_tasa
        FROM prestamos
        WHERE id IN (SELECT id FROM prestamos_backup_tasa_interes)
    """), {"nueva_tasa": Decimal(str(nueva_tasa))})
    
    row = resultado.fetchone()
    restantes_tasa_cero, con_nueva_tasa = row
    
    print(f"Préstamos con tasa 0% restantes: {restantes_tasa_cero}")
    print(f"Préstamos con nueva tasa ({nueva_tasa}%): {con_nueva_tasa:,}")
    
    if restantes_tasa_cero == 0 and con_nueva_tasa == total_tasa_cero:
        print("\n✅ ACTUALIZACION COMPLETADA EXITOSAMENTE")
    else:
        print("\n⚠️ Verificar: Puede haber inconsistencias")
    
    # Ver distribución final
    print("\n7. DISTRIBUCION FINAL DE TASAS:")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT 
            tasa_interes,
            COUNT(*) AS cantidad
        FROM prestamos
        WHERE estado = 'APROBADO'
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
    print(f"\n❌ ERROR durante la actualización: {type(e).__name__}")
    print(f"   {str(e)}")
    print("\n   Se hizo rollback. Los datos no se modificaron.")
    sys.exit(1)

finally:
    db.close()

print("\n" + "=" * 70)
print("NOTA: Las cuotas existentes NO se recalcularon automáticamente")
print("      Si necesitas recalcular cuotas con la nueva tasa, ejecuta:")
print("      scripts/python/recalcular_cuotas_con_nueva_tasa.py")
print("=" * 70)
