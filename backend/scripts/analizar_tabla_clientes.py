"""
Script para analizar la tabla clientes.

Muestra todas las variables (columnas) y todas las condiciones/restricciones
que maneja la tabla clientes.

USO:
    cd backend
    py scripts/analizar_tabla_clientes.py
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from sqlalchemy import text, inspect
from sqlalchemy.engine import Inspector

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def analizar_estructura_columnas(db, inspector: Inspector):
    """Analiza la estructura de columnas de la tabla clientes"""
    logger.info("=" * 60)
    logger.info("1. ESTRUCTURA DE COLUMNAS (VARIABLES)")
    logger.info("=" * 60)
    logger.info("")
    
    columns = inspector.get_columns('clientes')
    
    logger.info(f"{'Columna':<25} {'Tipo':<20} {'Nullable':<10} {'Default':<30}")
    logger.info("-" * 85)
    
    for col in columns:
        tipo = str(col['type'])
        nullable = "SÍ" if col['nullable'] else "NO"
        default = str(col.get('default', 'Sin default'))[:28]
        logger.info(f"{col['name']:<25} {tipo:<20} {nullable:<10} {default:<30}")
    
    logger.info("")


def analizar_constraints(db, inspector: Inspector):
    """Analiza todas las restricciones de la tabla"""
    logger.info("=" * 60)
    logger.info("2. RESTRICCIONES (CONSTRAINTS)")
    logger.info("=" * 60)
    logger.info("")
    
    # Primary Key
    pk_constraint = inspector.get_pk_constraint('clientes')
    if pk_constraint['constrained_columns']:
        logger.info(f"🔑 PRIMARY KEY: {', '.join(pk_constraint['constrained_columns'])}")
        logger.info(f"   Nombre: {pk_constraint['name']}")
        logger.info("")
    
    # Foreign Keys
    fks = inspector.get_foreign_keys('clientes')
    if fks:
        logger.info("🔗 FOREIGN KEYS SALIENTES (clientes → otras tablas):")
        for fk in fks:
            logger.info(f"   {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")
            logger.info(f"   Nombre: {fk['name']}")
        logger.info("")
    else:
        logger.info("   No hay Foreign Keys salientes")
        logger.info("")
    
    # Índices
    indexes = inspector.get_indexes('clientes')
    if indexes:
        logger.info("📊 ÍNDICES:")
        for idx in indexes:
            unique = "UNIQUE" if idx.get('unique', False) else "NORMAL"
            logger.info(f"   {idx['name']:<30} Columnas: {', '.join(idx['column_names'])} ({unique})")
        logger.info("")
    else:
        logger.info("   No hay índices adicionales")
        logger.info("")


def analizar_foreign_keys_entrantes(db):
    """Analiza Foreign Keys de otras tablas que referencian a clientes"""
    logger.info("=" * 60)
    logger.info("3. FOREIGN KEYS ENTRANTES (otras tablas → clientes)")
    logger.info("=" * 60)
    logger.info("")
    
    query = text("""
        SELECT 
            tc.table_name as tabla_origen,
            kcu.column_name as columna_fk,
            tc.constraint_name as nombre_fk
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu 
            ON ccu.constraint_name = tc.constraint_name
        WHERE ccu.table_schema = 'public' 
          AND ccu.table_name = 'clientes'
          AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name, kcu.ordinal_position
    """)
    
    result = db.execute(query)
    rows = result.fetchall()
    
    if rows:
        logger.info(f"{'Tabla Origen':<30} {'Columna FK':<25} {'Nombre Constraint':<30}")
        logger.info("-" * 85)
        for row in rows:
            logger.info(f"{row[0]:<30} {row[1]:<25} {row[2]:<30}")
    else:
        logger.info("   No hay Foreign Keys entrantes (otras tablas no referencian a clientes)")
    
    logger.info("")


def analizar_valores_unicos(db):
    """Analiza valores únicos en campos importantes"""
    logger.info("=" * 60)
    logger.info("4. VALORES ÚNICOS Y DISTINTOS")
    logger.info("=" * 60)
    logger.info("")
    
    # Estado
    query = text("""
        SELECT 
            estado,
            COUNT(*) as cantidad,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM clientes), 2) as porcentaje
        FROM clientes
        GROUP BY estado
        ORDER BY cantidad DESC
    """)
    result = db.execute(query)
    logger.info("📊 Valores en campo 'estado':")
    for row in result:
        logger.info(f"   {row[0]:<20} - {row[1]:>6} registros ({row[2]:>5}%)")
    logger.info("")
    
    # Activo
    query = text("""
        SELECT 
            activo,
            COUNT(*) as cantidad,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM clientes), 2) as porcentaje
        FROM clientes
        GROUP BY activo
        ORDER BY activo DESC
    """)
    result = db.execute(query)
    logger.info("📊 Valores en campo 'activo':")
    for row in result:
        logger.info(f"   {row[0]:<20} - {row[1]:>6} registros ({row[2]:>5}%)")
    logger.info("")
    
    # Cédulas duplicadas
    query = text("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT cedula) as unicas,
            COUNT(*) - COUNT(DISTINCT cedula) as duplicadas
        FROM clientes
    """)
    result = db.execute(query)
    row = result.fetchone()
    if row:
        logger.info("📊 Estadísticas de cédulas:")
        logger.info(f"   Total registros: {row[0]}")
        logger.info(f"   Cédulas únicas: {row[1]}")
        logger.info(f"   Cédulas duplicadas: {row[2]}")
        if row[0] > 0:
            porcentaje = round((row[2] / row[0]) * 100, 2)
            logger.info(f"   Porcentaje duplicados: {porcentaje}%")
    logger.info("")


def analizar_estadisticas(db):
    """Analiza estadísticas generales de la tabla"""
    logger.info("=" * 60)
    logger.info("5. ESTADÍSTICAS GENERALES")
    logger.info("=" * 60)
    logger.info("")
    
    queries = [
        ("Total de registros", "SELECT COUNT(*) FROM clientes"),
        ("Registros activos", "SELECT COUNT(*) FROM clientes WHERE activo = true"),
        ("Registros inactivos", "SELECT COUNT(*) FROM clientes WHERE activo = false"),
        ("Estado ACTIVO", "SELECT COUNT(*) FROM clientes WHERE estado = 'ACTIVO'"),
        ("Estado INACTIVO", "SELECT COUNT(*) FROM clientes WHERE estado = 'INACTIVO'"),
        ("Estado FINALIZADO", "SELECT COUNT(*) FROM clientes WHERE estado = 'FINALIZADO'"),
        ("Registros último mes", "SELECT COUNT(*) FROM clientes WHERE fecha_registro >= NOW() - INTERVAL '30 days'"),
    ]
    
    for nombre, query_sql in queries:
        try:
            result = db.execute(text(query_sql))
            valor = result.scalar()
            logger.info(f"   {nombre:<30} {valor:>10}")
        except Exception as e:
            logger.warning(f"   ⚠️  Error en {nombre}: {e}")
    
    logger.info("")


def analizar_valores_por_defecto(db):
    """Analiza valores por defecto y datos inválidos"""
    logger.info("=" * 60)
    logger.info("6. VALORES POR DEFECTO Y VALIDACIONES")
    logger.info("=" * 60)
    logger.info("")
    
    queries = [
        ("Emails con 'noemail'", "SELECT COUNT(*) FROM clientes WHERE email LIKE '%noemail%' OR email LIKE '%@noemail%'"),
        ("Teléfonos con '999999999'", "SELECT COUNT(*) FROM clientes WHERE telefono LIKE '%999999999%'"),
        ("Direcciones con 'Actualizar'", "SELECT COUNT(*) FROM clientes WHERE direccion LIKE '%Actualizar%'"),
        ("Ocupaciones con 'Actualizar'", "SELECT COUNT(*) FROM clientes WHERE ocupacion LIKE '%Actualizar%'"),
        ("Emails inválidos", "SELECT COUNT(*) FROM clientes WHERE email NOT LIKE '%@%.%' OR email = ''"),
    ]
    
    for nombre, query_sql in queries:
        try:
            result = db.execute(text(query_sql))
            valor = result.scalar()
            logger.info(f"   {nombre:<30} {valor:>10}")
        except Exception as e:
            logger.warning(f"   ⚠️  Error en {nombre}: {e}")
    
    logger.info("")


def analizar_longitudes(db):
    """Analiza longitudes de campos de texto"""
    logger.info("=" * 60)
    logger.info("7. LONGITUDES DE CAMPOS")
    logger.info("=" * 60)
    logger.info("")
    
    campos = ['cedula', 'nombres', 'telefono', 'email']
    
    logger.info(f"{'Campo':<15} {'Min':<8} {'Max':<8} {'Promedio':<10}")
    logger.info("-" * 45)
    
    for campo in campos:
        try:
            query = text(f"""
                SELECT 
                    MIN(LENGTH({campo})) as min_len,
                    MAX(LENGTH({campo})) as max_len,
                    AVG(LENGTH({campo}))::numeric(10,2) as avg_len
                FROM clientes
            """)
            result = db.execute(query)
            row = result.fetchone()
            if row:
                logger.info(f"{campo:<15} {row[0] or 0:<8} {row[1] or 0:<8} {float(row[2] or 0):<10.2f}")
        except Exception as e:
            logger.warning(f"   ⚠️  Error analizando {campo}: {e}")
    
    logger.info("")


def generar_resumen(db, inspector: Inspector):
    """Genera un resumen ejecutivo"""
    logger.info("=" * 60)
    logger.info("8. RESUMEN EJECUTIVO")
    logger.info("=" * 60)
    logger.info("")
    
    # Total de columnas
    columns = inspector.get_columns('clientes')
    logger.info(f"   Total de columnas: {len(columns)}")
    
    # Primary Keys
    pk = inspector.get_pk_constraint('clientes')
    logger.info(f"   Primary Keys: {len(pk.get('constrained_columns', []))}")
    
    # Foreign Keys
    fks = inspector.get_foreign_keys('clientes')
    logger.info(f"   Foreign Keys salientes: {len(fks)}")
    
    # Índices
    indexes = inspector.get_indexes('clientes')
    logger.info(f"   Índices: {len(indexes)}")
    
    # Total registros
    result = db.execute(text("SELECT COUNT(*) FROM clientes"))
    total = result.scalar()
    logger.info(f"   Total de registros: {total}")
    
    logger.info("")


def main():
    """Función principal"""
    db = SessionLocal()
    
    try:
        inspector = inspect(db.bind)
        
        # Verificar que la tabla existe
        if 'clientes' not in inspector.get_table_names():
            logger.error("❌ La tabla 'clientes' no existe en la base de datos")
            return
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("🔍 ANÁLISIS COMPLETO DE LA TABLA: clientes")
        logger.info("=" * 60)
        logger.info("")
        
        # Ejecutar análisis
        analizar_estructura_columnas(db, inspector)
        analizar_constraints(db, inspector)
        analizar_foreign_keys_entrantes(db)
        analizar_valores_unicos(db)
        analizar_estadisticas(db)
        analizar_valores_por_defecto(db)
        analizar_longitudes(db)
        generar_resumen(db, inspector)
        
        logger.info("=" * 60)
        logger.info("✅ ANÁLISIS COMPLETO")
        logger.info("=" * 60)
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Error al analizar la tabla: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

