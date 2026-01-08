"""Confirmar que el backup contiene todos los préstamos con tasa 0%"""
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
print("CONFIRMACION: BACKUP CON TASA 0%")
print("=" * 70)

# 1. Verificar backup
print("\n1. VERIFICANDO BACKUP:")
print("-" * 70)

try:
    # Contar total en backup
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total_backup,
            COUNT(DISTINCT id) AS ids_unicos,
            MIN(fecha_backup) AS fecha_backup_min,
            MAX(fecha_backup) AS fecha_backup_max
        FROM prestamos_backup_tasa_interes
    """))
    
    row = resultado.fetchone()
    total_backup, ids_unicos, fecha_min, fecha_max = row
    
    print(f"Total registros en backup: {total_backup:,}")
    print(f"IDs únicos en backup: {ids_unicos:,}")
    print(f"Fecha del backup: {fecha_min}")
    
    # Verificar tasas en el backup
    resultado = db.execute(text("""
        SELECT 
            tasa_interes,
            COUNT(*) AS cantidad,
            COUNT(DISTINCT id) AS ids_unicos
        FROM prestamos_backup_tasa_interes
        GROUP BY tasa_interes
        ORDER BY tasa_interes
    """))
    
    print(f"\n   Distribución de tasas en backup:")
    print(f"{'Tasa Interés':<15} {'Cantidad':<12} {'IDs Únicos':<12}")
    print("-" * 45)
    
    total_con_tasa_cero = 0
    for row in resultado.fetchall():
        tasa, cantidad, ids = row
        print(f"{tasa:<15} {cantidad:<12} {ids:<12}")
        if tasa == 0.00:
            total_con_tasa_cero = cantidad
    
    # 2. Comparar con estado actual
    print("\n2. COMPARANDO CON ESTADO ACTUAL:")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total_prestamos,
            COUNT(CASE WHEN tasa_interes = 0.00 THEN 1 END) AS con_tasa_cero
        FROM prestamos
    """))
    
    row = resultado.fetchone()
    total_prestamos_actual, con_tasa_cero_actual = row
    
    print(f"Total préstamos actuales: {total_prestamos_actual:,}")
    print(f"Préstamos con tasa 0% actuales: {con_tasa_cero_actual:,}")
    print(f"\nTotal en backup: {total_backup:,}")
    print(f"Préstamos con tasa 0% en backup: {total_con_tasa_cero:,}")
    
    # 3. Verificar coincidencia
    print("\n3. VERIFICACION DE COINCIDENCIA:")
    print("-" * 70)
    
    # Verificar que todos los IDs del backup tienen tasa 0%
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total_backup,
            COUNT(CASE WHEN tasa_interes = 0.00 THEN 1 END) AS con_tasa_cero_en_backup
        FROM prestamos_backup_tasa_interes
    """))
    
    row = resultado.fetchone()
    total_backup_verificacion, con_tasa_cero_backup = row
    
    if con_tasa_cero_backup == total_backup_verificacion:
        print("✅ CONFIRMADO: TODOS los préstamos en el backup tienen tasa 0%")
        print(f"   Total en backup: {total_backup_verificacion:,}")
        print(f"   Con tasa 0%: {con_tasa_cero_backup:,} (100%)")
    else:
        print("❌ NO CONFIRMADO: No todos los préstamos en backup tienen tasa 0%")
        print(f"   Total en backup: {total_backup_verificacion:,}")
        print(f"   Con tasa 0%: {con_tasa_cero_backup:,}")
    
    # 4. Verificar que el backup coincide con el estado actual
    print("\n4. VERIFICACION DE CONSISTENCIA:")
    print("-" * 70)
    
    if total_backup == total_prestamos_actual:
        print(f"✅ Coincidencia de cantidad: {total_backup:,} préstamos")
    else:
        print(f"⚠️ Diferencia en cantidad:")
        print(f"   Backup: {total_backup:,}")
        print(f"   Actual: {total_prestamos_actual:,}")
        print(f"   Diferencia: {abs(total_backup - total_prestamos_actual):,}")
    
    if con_tasa_cero_backup == con_tasa_cero_actual:
        print(f"✅ Coincidencia de tasa 0%: {con_tasa_cero_backup:,} préstamos")
    else:
        print(f"⚠️ Diferencia en tasa 0%:")
        print(f"   Backup: {con_tasa_cero_backup:,}")
        print(f"   Actual: {con_tasa_cero_actual:,}")
        print(f"   Diferencia: {abs(con_tasa_cero_backup - con_tasa_cero_actual):,}")
    
    # 5. Verificar IDs específicos
    print("\n5. VERIFICACION DE IDs:")
    print("-" * 70)
    
    # Verificar que todos los IDs del backup existen en préstamos actuales
    resultado = db.execute(text("""
        SELECT 
            COUNT(DISTINCT b.id) AS ids_backup,
            COUNT(DISTINCT p.id) AS ids_encontrados
        FROM prestamos_backup_tasa_interes b
        LEFT JOIN prestamos p ON b.id = p.id
    """))
    
    row = resultado.fetchone()
    ids_backup, ids_encontrados = row
    
    print(f"IDs únicos en backup: {ids_backup:,}")
    print(f"IDs encontrados en préstamos actuales: {ids_encontrados:,}")
    
    if ids_backup == ids_encontrados:
        print("✅ Todos los IDs del backup existen en préstamos actuales")
    else:
        print(f"⚠️ {ids_backup - ids_encontrados:,} IDs del backup no existen en préstamos actuales")
    
    # 6. Resumen final
    print("\n6. RESUMEN FINAL:")
    print("-" * 70)
    
    confirmacion_completa = (
        con_tasa_cero_backup == total_backup_verificacion and
        con_tasa_cero_backup == total_backup and
        total_backup == total_prestamos_actual
    )
    
    if confirmacion_completa:
        print("✅ CONFIRMADO COMPLETAMENTE:")
        print(f"   - El backup contiene {total_backup:,} préstamos")
        print(f"   - TODOS los préstamos en backup tienen tasa 0%")
        print(f"   - La cantidad coincide con préstamos actuales")
        print(f"   - La lógica de tasa 0% está presente en el backup")
    else:
        print("⚠️ VERIFICAR:")
        print(f"   - Backup: {total_backup:,} préstamos")
        print(f"   - Con tasa 0% en backup: {con_tasa_cero_backup:,}")
        print(f"   - Préstamos actuales: {total_prestamos_actual:,}")
        print(f"   - Con tasa 0% actuales: {con_tasa_cero_actual:,}")
    
except Exception as e:
    print(f"\n❌ ERROR al verificar backup: {type(e).__name__}")
    print(f"   {str(e)}")
    db.rollback()

finally:
    db.close()

print("\n" + "=" * 70)
