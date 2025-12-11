"""
Script de ejemplo para reemplazar datos en la base de datos.

Este script muestra cómo reemplazar datos de forma segura usando transacciones.

USO:
    cd backend
    py scripts/reemplazar_datos_ejemplo.py

IMPORTANTE:
    - Hacer backup de la base de datos antes de ejecutar
    - Revisar y modificar las consultas según tus necesidades
    - Este es un ejemplo - personalizar según tus requerimientos
"""

import sys
import logging
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from sqlalchemy import text

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reemplazar_datos_seguro():
    """
    Reemplaza datos de forma segura usando transacciones.
    
    Este es un ejemplo - modificar según tus necesidades específicas.
    """
    db = SessionLocal()
    
    try:
        logger.info("🔄 Iniciando reemplazo de datos...")
        
        # =====================================================
        # EJEMPLO 1: Reemplazar valores específicos
        # =====================================================
        logger.info("📝 Ejemplo 1: Reemplazando concesionarios 'NO DEFINIDO'...")
        
        # Verificar cuántos registros se van a afectar
        result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM prestamos 
            WHERE concesionario = 'NO DEFINIDO'
        """))
        count = result.scalar()
        logger.info(f"   Registros a actualizar: {count}")
        
        if count > 0:
            # Reemplazar los datos
            db.execute(text("""
                UPDATE prestamos 
                SET concesionario = 'SIN ASIGNAR'
                WHERE concesionario = 'NO DEFINIDO'
            """))
            logger.info(f"   ✅ {count} registros actualizados")
        else:
            logger.info("   ℹ️ No hay registros para actualizar")
        
        # =====================================================
        # EJEMPLO 2: Reemplazar múltiples valores
        # =====================================================
        logger.info("📝 Ejemplo 2: Normalizando valores de analista...")
        
        # Mapeo de valores antiguos a nuevos
        reemplazos = {
            'ANALISTA 1': 'Analista Principal',
            'ANALISTA 2': 'Analista Secundario',
            'ANALISTA 3': 'Analista Terciario',
        }
        
        for valor_antiguo, valor_nuevo in reemplazos.items():
            result = db.execute(text("""
                SELECT COUNT(*) as total
                FROM prestamos 
                WHERE analista = :antiguo
            """), {'antiguo': valor_antiguo})
            count = result.scalar()
            
            if count > 0:
                db.execute(text("""
                    UPDATE prestamos 
                    SET analista = :nuevo
                    WHERE analista = :antiguo
                """), {'nuevo': valor_nuevo, 'antiguo': valor_antiguo})
                logger.info(f"   ✅ {count} registros: '{valor_antiguo}' → '{valor_nuevo}'")
        
        # =====================================================
        # EJEMPLO 3: Reemplazar basado en condición compleja
        # =====================================================
        logger.info("📝 Ejemplo 3: Reemplazando valores basado en condición...")
        
        db.execute(text("""
            UPDATE prestamos 
            SET estado = 'ACTIVO'
            WHERE estado IS NULL 
               OR estado = ''
               OR estado = 'PENDIENTE'
        """))
        
        result = db.execute(text("SELECT COUNT(*) FROM prestamos WHERE estado = 'ACTIVO'"))
        count = result.scalar()
        logger.info(f"   ✅ Préstamos con estado 'ACTIVO': {count}")
        
        # =====================================================
        # VERIFICAR CAMBIOS
        # =====================================================
        logger.info("🔍 Verificando cambios...")
        
        # Verificar concesionarios
        result = db.execute(text("""
            SELECT concesionario, COUNT(*) as total
            FROM prestamos 
            GROUP BY concesionario
            ORDER BY total DESC
            LIMIT 10
        """))
        logger.info("   Top 10 concesionarios:")
        for row in result:
            logger.info(f"      {row.concesionario}: {row.total}")
        
        # =====================================================
        # HACER COMMIT
        # =====================================================
        db.commit()
        logger.info("✅ Cambios guardados correctamente (COMMIT realizado)")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error al reemplazar datos: {e}")
        logger.error("   Cambios revertidos (ROLLBACK realizado)")
        raise
    finally:
        db.close()
        logger.info("🔒 Conexión cerrada")


def reemplazar_datos_desde_archivo(archivo_csv: str):
    """
    Reemplaza datos desde un archivo CSV.
    
    Args:
        archivo_csv: Ruta al archivo CSV con los datos nuevos
    """
    import pandas as pd
    
    logger.info(f"📂 Leyendo archivo: {archivo_csv}")
    df = pd.read_csv(archivo_csv)
    
    db = SessionLocal()
    try:
        logger.info(f"📝 Procesando {len(df)} registros...")
        
        for index, row in df.iterrows():
            db.execute(text("""
                UPDATE prestamos 
                SET concesionario = :concesionario,
                    analista = :analista
                WHERE id = :id
            """), {
                'id': row['id'],
                'concesionario': row.get('concesionario'),
                'analista': row.get('analista'),
            })
            
            if (index + 1) % 100 == 0:
                logger.info(f"   Procesados {index + 1}/{len(df)} registros...")
        
        db.commit()
        logger.info("✅ Datos importados y reemplazados correctamente")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Reemplazar datos en la base de datos')
    parser.add_argument(
        '--archivo',
        type=str,
        help='Ruta al archivo CSV con datos a importar (opcional)'
    )
    
    args = parser.parse_args()
    
    if args.archivo:
        reemplazar_datos_desde_archivo(args.archivo)
    else:
        # Ejecutar ejemplo básico
        print("=" * 60)
        print("⚠️  ADVERTENCIA: Este script modificará datos en la base de datos")
        print("=" * 60)
        print()
        respuesta = input("¿Has hecho backup de la base de datos? (s/n): ")
        
        if respuesta.lower() != 's':
            print("❌ Por favor, haz backup primero antes de continuar")
            sys.exit(1)
        
        print()
        reemplazar_datos_seguro()

