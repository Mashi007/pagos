"""
Script para verificar el estado antes de aplicar Fase 1: Integridad Referencial
Verifica:
1. Cuotas huérfanas (sin préstamo válido)
2. Estado actual de Foreign Keys en tabla cuotas
3. Índices existentes en cuotas.prestamo_id
4. Preparación para crear Foreign Key
"""

import sys
from pathlib import Path

# Agregar el directorio raíz y backend al path para importar módulos
root_dir = Path(__file__).parent.parent
backend_dir = root_dir / "backend"
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from datetime import datetime

def print_section(title: str):
    """Imprime un separador de sección"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_subsection(title: str):
    """Imprime un separador de subsección"""
    print(f"\n--- {title} ---")

def verificar_cuotas_huerfanas(db):
    """Verifica si hay cuotas con prestamo_id inválido"""
    print_subsection("1. Verificación de Cuotas Huérfanas")
    
    # Cuotas sin préstamo válido
    resultado = db.execute(text("""
        SELECT COUNT(*) as total_huerfanas
        FROM cuotas c
        LEFT JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.id IS NULL
    """)).fetchone()
    
    total_huerfanas = resultado[0] if resultado else 0
    
    if total_huerfanas > 0:
        print(f"ERROR: Se encontraron {total_huerfanas} cuotas huérfanas (sin préstamo válido)")
        
        # Detalles de cuotas huérfanas
        detalles = db.execute(text("""
            SELECT c.id, c.prestamo_id, c.numero_cuota, c.estado, c.monto_cuota
            FROM cuotas c
            LEFT JOIN prestamos p ON c.prestamo_id = p.id
            WHERE p.id IS NULL
            ORDER BY c.prestamo_id, c.numero_cuota
            LIMIT 20
        """)).fetchall()
        
        print("\nPrimeras 20 cuotas huérfanas:")
        for cuota_id, prestamo_id, numero_cuota, estado, monto_cuota in detalles:
            print(f"   - Cuota ID {cuota_id}: prestamo_id={prestamo_id}, cuota #{numero_cuota}, estado={estado}, monto=${monto_cuota}")
        
        return False, total_huerfanas
    else:
        print("OK: No se encontraron cuotas huérfanas")
        return True, 0

def verificar_foreign_keys(db):
    """Verifica el estado actual de Foreign Keys en tabla cuotas"""
    print_subsection("2. Verificación de Foreign Keys Existentes")
    
    inspector = inspect(db.bind)
    
    # Obtener Foreign Keys de la tabla cuotas
    fks = inspector.get_foreign_keys('cuotas')
    
    print(f"Foreign Keys encontradas en tabla 'cuotas': {len(fks)}")
    
    fk_prestamo_encontrada = False
    for fk in fks:
        print(f"   - {fk['name']}: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
        if 'prestamo_id' in fk['constrained_columns'] and fk['referred_table'] == 'prestamos':
            fk_prestamo_encontrada = True
            print(f"     ✓ Foreign Key para prestamo_id ya existe")
    
    if not fk_prestamo_encontrada:
        print("\nADVERTENCIA: No existe Foreign Key para cuotas.prestamo_id -> prestamos.id")
        print("   Se necesita crear esta Foreign Key")
    
    return fk_prestamo_encontrada

def verificar_indices(db):
    """Verifica índices existentes en cuotas.prestamo_id"""
    print_subsection("3. Verificación de Índices en cuotas.prestamo_id")
    
    inspector = inspect(db.bind)
    indexes = inspector.get_indexes('cuotas')
    
    print(f"Índices encontrados en tabla 'cuotas': {len(indexes)}")
    
    indice_prestamo_encontrado = False
    for idx in indexes:
        col_names = [str(c) for c in idx.get('column_names', []) if c is not None]
        cols_str = ", ".join(col_names)
        unique = "UNIQUE" if idx.get('unique', False) else ""
        print(f"   - {idx.get('name', 'sin_nombre')}: {cols_str} {unique}")
        
        if 'prestamo_id' in col_names:
            indice_prestamo_encontrado = True
            print(f"     ✓ Índice en prestamo_id ya existe")
    
    if not indice_prestamo_encontrado:
        print("\nADVERTENCIA: No existe índice en cuotas.prestamo_id")
        print("   Se recomienda crear un índice para mejorar rendimiento")
    
    return indice_prestamo_encontrado

def verificar_estadisticas_cuotas(db):
    """Muestra estadísticas generales de cuotas"""
    print_subsection("4. Estadísticas Generales de Cuotas")
    
    # Total de cuotas
    total = db.execute(text("SELECT COUNT(*) FROM cuotas")).scalar()
    print(f"Total de cuotas: {total:,}")
    
    # Cuotas por estado
    por_estado = db.execute(text("""
        SELECT estado, COUNT(*) as cantidad
        FROM cuotas
        GROUP BY estado
        ORDER BY cantidad DESC
    """)).fetchall()
    
    print("\nCuotas por estado:")
    for estado, cantidad in por_estado:
        print(f"   - {estado}: {cantidad:,}")
    
    # Cuotas con préstamo válido
    con_prestamo_valido = db.execute(text("""
        SELECT COUNT(*)
        FROM cuotas c
        INNER JOIN prestamos p ON c.prestamo_id = p.id
    """)).scalar()
    
    print(f"\nCuotas con préstamo válido: {con_prestamo_valido:,}")
    print(f"Porcentaje válidas: {(con_prestamo_valido/total*100):.2f}%")

def verificar_prestamos_relacionados(db):
    """Verifica préstamos que tienen cuotas"""
    print_subsection("5. Verificación de Préstamos y Cuotas")
    
    # Préstamos con cuotas
    prestamos_con_cuotas = db.execute(text("""
        SELECT COUNT(DISTINCT p.id)
        FROM prestamos p
        INNER JOIN cuotas c ON p.id = c.prestamo_id
    """)).scalar()
    
    # Total de préstamos aprobados
    total_aprobados = db.execute(text("""
        SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO'
    """)).scalar()
    
    print(f"Préstamos aprobados: {total_aprobados:,}")
    print(f"Préstamos con cuotas: {prestamos_con_cuotas:,}")
    
    # Préstamos aprobados sin cuotas
    aprobados_sin_cuotas = db.execute(text("""
        SELECT COUNT(*)
        FROM prestamos p
        LEFT JOIN cuotas c ON p.id = c.prestamo_id
        WHERE p.estado = 'APROBADO' AND c.id IS NULL
    """)).scalar()
    
    if aprobados_sin_cuotas > 0:
        print(f"ADVERTENCIA: {aprobados_sin_cuotas} préstamos aprobados sin cuotas")
    else:
        print("OK: Todos los préstamos aprobados tienen cuotas")

def generar_migracion_sugerida():
    """Genera el código sugerido para la migración"""
    print_section("CÓDIGO SUGERIDO PARA MIGRACIÓN")
    
    codigo = '''"""
Migración: Agregar Foreign Key cuotas.prestamo_id -> prestamos.id
Fecha: {fecha}
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'XXXX_add_fk_cuotas_prestamo_id'
down_revision = 'XXXX_previous_revision'  # Reemplazar con la revisión anterior
branch_labels = None
depends_on = None

def upgrade():
    """Agregar Foreign Key y índice a cuotas.prestamo_id"""
    
    # PASO 1: Eliminar cuotas huérfanas (si existen)
    # ADVERTENCIA: Revisar antes de ejecutar
    op.execute("""
        DELETE FROM cuotas 
        WHERE prestamo_id NOT IN (SELECT id FROM prestamos)
    """)
    
    # PASO 2: Crear índice si no existe
    # Verificar primero si existe el índice
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_id 
        ON cuotas(prestamo_id)
    """)
    
    # PASO 3: Crear Foreign Key
    op.create_foreign_key(
        'fk_cuotas_prestamo_id',
        'cuotas', 'prestamos',
        ['prestamo_id'], ['id'],
        ondelete='CASCADE',
        onupdate='CASCADE'
    )

def downgrade():
    """Eliminar Foreign Key e índice"""
    op.drop_constraint('fk_cuotas_prestamo_id', 'cuotas', type_='foreignkey')
    op.drop_index('idx_cuotas_prestamo_id', table_name='cuotas')
'''.format(fecha=datetime.now().strftime('%Y-%m-%d'))
    
    print(codigo)
    print("\n" + "="*80)
    print("INSTRUCCIONES:")
    print("="*80)
    print("1. Ejecutar: cd backend && alembic revision -m 'add_fk_cuotas_prestamo_id'")
    print("2. Copiar el código sugerido arriba en el archivo de migración generado")
    print("3. Reemplazar 'XXXX_previous_revision' con la revisión anterior real")
    print("4. Revisar y ajustar según sea necesario")
    print("5. Ejecutar: alembic upgrade head")

def main():
    """Función principal"""
    import os
    
    # Configurar encoding UTF-8 para Windows
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    
    print_section("VERIFICACIÓN FASE 1: INTEGRIDAD REFERENCIAL")
    print(f"Fecha de verificación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Conectar a BD
    try:
        from urllib.parse import urlparse, urlunparse, quote_plus
        from dotenv import load_dotenv
        
        env_file = root_dir / ".env"
        if not env_file.exists():
            env_file = backend_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=False)
        
        db_url_raw = os.getenv("DATABASE_URL", str(settings.DATABASE_URL))
        
        parsed = urlparse(db_url_raw)
        username = quote_plus(parsed.username) if parsed.username else None
        password = quote_plus(parsed.password) if parsed.password else None
        
        if username and password:
            netloc = f"{username}:{password}@{parsed.hostname}"
        elif username:
            netloc = f"{username}@{parsed.hostname}"
        else:
            netloc = parsed.hostname
        
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        
        db_url = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
        
        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
    except Exception as e:
        print(f"ERROR: No se pudo conectar a la base de datos: {str(e)}")
        return
    
    try:
        # Ejecutar verificaciones
        sin_huerfanas, total_huerfanas = verificar_cuotas_huerfanas(db)
        fk_existe = verificar_foreign_keys(db)
        indice_existe = verificar_indices(db)
        verificar_estadisticas_cuotas(db)
        verificar_prestamos_relacionados(db)
        
        # Resumen final
        print_section("RESUMEN Y RECOMENDACIONES")
        
        problemas = []
        advertencias = []
        
        if not sin_huerfanas:
            problemas.append(f"Existen {total_huerfanas} cuotas huérfanas que deben eliminarse antes de crear la FK")
        
        if not fk_existe:
            problemas.append("Falta Foreign Key en cuotas.prestamo_id -> prestamos.id")
        
        if not indice_existe:
            advertencias.append("Falta índice en cuotas.prestamo_id (recomendado para rendimiento)")
        
        if problemas:
            print("PROBLEMAS CRÍTICOS encontrados:")
            for i, problema in enumerate(problemas, 1):
                print(f"   {i}. {problema}")
            print("\n⚠️  ACCIÓN REQUERIDA: Resolver estos problemas antes de crear la Foreign Key")
        else:
            print("OK: No se encontraron problemas críticos")
            print("✓ Se puede proceder con la creación de la Foreign Key")
        
        if advertencias:
            print("\nADVERTENCIAS:")
            for i, advertencia in enumerate(advertencias, 1):
                print(f"   {i}. {advertencia}")
        
        # Generar código de migración
        if sin_huerfanas and not fk_existe:
            generar_migracion_sugerida()
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
