"""Ejecutar eliminación de cuotas huérfanas sin pagos"""
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
print("ELIMINACION DE CUOTAS HUERFANAS SIN PAGOS")
print("=" * 70)

try:
    # 1. Crear backup
    print("\n1. CREANDO BACKUP...")
    print("-" * 70)
    
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS cuotas_huerfanas_backup_eliminacion AS
        SELECT 
            *,
            CURRENT_TIMESTAMP AS fecha_backup
        FROM cuotas
        WHERE prestamo_id BETWEEN 1 AND 3784
    """))
    db.commit()
    
    resultado = db.execute(text("SELECT COUNT(*) FROM cuotas_huerfanas_backup_eliminacion"))
    total_backup = resultado.scalar()
    print(f"✅ Backup creado: {total_backup:,} cuotas guardadas")
    
    # 2. Verificar cuotas a eliminar
    print("\n2. VERIFICANDO CUOTAS A ELIMINAR...")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total_sin_pagos,
            COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS con_pagos
        FROM cuotas
        WHERE prestamo_id BETWEEN 1 AND 3784
    """))
    
    row = resultado.fetchone()
    total_sin_pagos, con_pagos = row
    
    print(f"Cuotas huérfanas sin pagos a eliminar: {total_sin_pagos:,}")
    print(f"Cuotas huérfanas con pagos a mantener: {con_pagos:,}")
    
    # 3. Verificar préstamos aprobados
    print("\n3. VERIFICANDO PRESTAMOS APROBADOS...")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT COUNT(DISTINCT p.id) AS prestamos_aprobados
        FROM prestamos p
        INNER JOIN cuotas c ON p.id = c.prestamo_id
        WHERE p.estado = 'APROBADO'
          AND c.prestamo_id BETWEEN 3785 AND 7826
    """))
    
    prestamos_aprobados = resultado.scalar()
    print(f"Préstamos aprobados con cuotas propias: {prestamos_aprobados:,}")
    
    if prestamos_aprobados != 4042:
        print("\n❌ ERROR: Los préstamos aprobados no tienen todas sus cuotas")
        print("   NO proceder con la eliminación")
        db.close()
        sys.exit(1)
    
    print("✅ Confirmado: Los préstamos aprobados están intactos")
    
    # 4. Eliminar cuotas huérfanas sin pagos
    print("\n4. ELIMINANDO CUOTAS HUERFANAS SIN PAGOS...")
    print("-" * 70)
    
    resultado = db.execute(text("""
        DELETE FROM cuotas
        WHERE prestamo_id BETWEEN 1 AND 3784
          AND total_pagado = 0
    """))
    
    db.commit()
    filas_eliminadas = resultado.rowcount
    print(f"✅ Eliminadas: {filas_eliminadas:,} cuotas huérfanas sin pagos")
    
    # 5. Verificar eliminación
    print("\n5. VERIFICANDO ELIMINACION...")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS cuotas_huerfanas_restantes,
            COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_pagos_mantenidas
        FROM cuotas
        WHERE prestamo_id BETWEEN 1 AND 3784
    """))
    
    row = resultado.fetchone()
    restantes, con_pagos_mantenidas = row
    
    print(f"Cuotas huérfanas restantes: {restantes:,}")
    print(f"Cuotas con pagos mantenidas: {con_pagos_mantenidas:,}")
    
    # Verificar préstamos aprobados
    resultado = db.execute(text("""
        SELECT COUNT(DISTINCT p.id) AS prestamos_aprobados
        FROM prestamos p
        INNER JOIN cuotas c ON p.id = c.prestamo_id
        WHERE p.estado = 'APROBADO'
          AND c.prestamo_id BETWEEN 3785 AND 7826
    """))
    
    prestamos_aprobados_post = resultado.scalar()
    print(f"Préstamos aprobados después de eliminación: {prestamos_aprobados_post:,}")
    
    if prestamos_aprobados_post == 4042:
        print("✅ Los préstamos aprobados siguen intactos")
    else:
        print("❌ ERROR: Los préstamos aprobados se vieron afectados")
    
    # 6. Resumen final
    print("\n6. RESUMEN FINAL:")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total_cuotas_bd,
            COUNT(CASE WHEN prestamo_id BETWEEN 1 AND 3784 THEN 1 END) AS cuotas_huerfanas,
            COUNT(CASE WHEN prestamo_id BETWEEN 3785 AND 7826 THEN 1 END) AS cuotas_propias
        FROM cuotas
    """))
    
    row = resultado.fetchone()
    total_cuotas, huerfanas, propias = row
    
    print(f"Total cuotas en BD: {total_cuotas:,}")
    print(f"Cuotas huérfanas restantes: {huerfanas:,} (solo con pagos)")
    print(f"Cuotas propias de préstamos aprobados: {propias:,}")
    
    print("\n✅ ELIMINACION COMPLETADA EXITOSAMENTE")
    print(f"   - Eliminadas: {filas_eliminadas:,} cuotas sin pagos")
    print(f"   - Mantenidas: {con_pagos_mantenidas:,} cuotas con pagos (datos históricos)")
    print(f"   - Préstamos aprobados: {prestamos_aprobados_post:,} (intactos)")
    
except Exception as e:
    db.rollback()
    print(f"\n❌ ERROR durante la eliminación: {type(e).__name__}")
    print(f"   {str(e)}")
    print("\n   Se hizo rollback. Los datos no se modificaron.")
    sys.exit(1)

finally:
    db.close()

print("\n" + "=" * 70)
