"""Crear backup de tablas antes de ejecutar correcciones"""
import sys
import io
from pathlib import Path
from datetime import datetime

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Fecha para el backup
fecha_backup = datetime.now().strftime('%Y%m%d')

print("=" * 70)
print("CREAR BACKUP ANTES DE CORRECCIONES")
print("=" * 70)
print(f"\nFecha del backup: {fecha_backup}")
print("\nEste script crea backups de las siguientes tablas:")
print("  - cuotas (principal)")
print("  - prestamos")
print("  - pagos")
print("  - clientes")
print("\n" + "=" * 70)

# Tablas a respaldar
tablas = [
    'cuotas',
    'prestamos',
    'pagos',
    'clientes'
]

backups_creados = []
errores = []

for tabla in tablas:
    tabla_backup = f"{tabla}_backup_{fecha_backup}"
    
    print(f"\nCreando backup de tabla: {tabla}...")
    
    try:
        # Crear tabla de backup
        db.execute(
            text(f"CREATE TABLE {tabla_backup} AS SELECT * FROM {tabla}")
        )
        db.commit()
        
        # Verificar que se creó correctamente
        resultado = db.execute(
            text(f"SELECT COUNT(*) FROM {tabla_backup}")
        )
        registros_backup = resultado.scalar()
        
        resultado = db.execute(
            text(f"SELECT COUNT(*) FROM {tabla}")
        )
        registros_original = resultado.scalar()
        
        if registros_backup == registros_original:
            print(f"  [OK] Backup creado: {tabla_backup}")
            print(f"       Registros: {registros_backup}")
            backups_creados.append({
                'tabla': tabla,
                'backup': tabla_backup,
                'registros': registros_backup
            })
        else:
            print(f"  [ERROR] Diferencia en registros!")
            print(f"          Original: {registros_original}, Backup: {registros_backup}")
            errores.append({
                'tabla': tabla,
                'backup': tabla_backup,
                'error': f'Diferencia en registros: {registros_original} vs {registros_backup}'
            })
    
    except Exception as e:
        print(f"  [ERROR] No se pudo crear backup: {str(e)}")
        db.rollback()
        errores.append({
            'tabla': tabla,
            'backup': tabla_backup,
            'error': str(e)
        })

# Resumen
print("\n" + "=" * 70)
print("RESUMEN DE BACKUPS")
print("=" * 70)

if len(backups_creados) > 0:
    print(f"\n[OK] Backups creados exitosamente: {len(backups_creados)}")
    print("\nDetalle:")
    for backup in backups_creados:
        print(f"  - {backup['backup']}: {backup['registros']} registros")

if len(errores) > 0:
    print(f"\n[ERROR] Errores al crear backups: {len(errores)}")
    print("\nDetalle:")
    for error in errores:
        print(f"  - {error['tabla']}: {error['error']}")

# Verificar tamaño de backups
print("\n" + "=" * 70)
print("TAMAÑO DE BACKUPS")
print("=" * 70)

try:
    resultado = db.execute(
        text("""
            SELECT 
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS tamaño
            FROM pg_tables
            WHERE tablename LIKE :patron
            ORDER BY tablename
        """),
        {"patron": f"%_backup_{fecha_backup}"}
    )
    
    tamanos = resultado.fetchall()
    if len(tamanos) > 0:
        print("\nTamaño de cada backup:")
        total_tamano = 0
        for tabla, tamano in tamanos:
            print(f"  - {tabla}: {tamano}")
    else:
        print("\nNo se encontraron tablas de backup")
except Exception as e:
    print(f"\n[ADVERTENCIA] No se pudo obtener tamaño de backups: {str(e)}")

# Estadísticas de tablas originales
print("\n" + "=" * 70)
print("ESTADISTICAS DE TABLAS ORIGINALES")
print("=" * 70)

for tabla in tablas:
    try:
        # Para cuotas, usar fecha_vencimiento en lugar de fecha_registro
        if tabla == 'cuotas':
            fecha_col = 'fecha_vencimiento'
            fecha_label = 'Fecha vencimiento'
        else:
            fecha_col = 'fecha_registro'
            fecha_label = 'Registro'
        
        try:
            resultado = db.execute(
                text(f"""
                    SELECT 
                        COUNT(*) AS total_registros,
                        MIN({fecha_col}) AS fecha_mas_antigua,
                        MAX({fecha_col}) AS fecha_mas_reciente
                    FROM {tabla}
                """)
            )
            stats = resultado.fetchone()
            if stats:
                total, min_fecha, max_fecha = stats
                print(f"\n{tabla}:")
                print(f"  Total registros: {total}")
                if min_fecha:
                    print(f"  {fecha_label} mas antigua: {min_fecha}")
                if max_fecha:
                    print(f"  {fecha_label} mas reciente: {max_fecha}")
        except Exception as e:
            # Si la columna no existe, solo mostrar el conteo
            resultado = db.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
            total = resultado.scalar()
            print(f"\n{tabla}:")
            print(f"  Total registros: {total}")
    except Exception as e:
        print(f"\n[ADVERTENCIA] No se pudieron obtener estadisticas de {tabla}: {str(e)}")

# Instrucciones finales
print("\n" + "=" * 70)
print("INSTRUCCIONES")
print("=" * 70)

print("\n[IMPORTANTE] Backups creados con fecha:", fecha_backup)
print("\nPara restaurar un backup (si es necesario):")
print("  TRUNCATE TABLE cuotas;")
print(f"  INSERT INTO cuotas SELECT * FROM cuotas_backup_{fecha_backup};")
print("\nPara eliminar backups (después de verificar correcciones):")
for tabla in tablas:
    print(f"  DROP TABLE {tabla}_backup_{fecha_backup};")

if len(errores) == 0:
    print("\n[OK] Todos los backups se crearon correctamente")
    print("     Puede proceder con las correcciones")
else:
    print("\n[ATENCION] Hubo errores al crear algunos backups")
    print("           Revise los errores antes de continuar")

print("\n" + "=" * 70)

db.close()
