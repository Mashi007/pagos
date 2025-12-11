"""
Script para identificar tablas que apoyan procesos de CRM.

Este script analiza la base de datos y genera un reporte completo de:
- Tablas principales de CRM
- Relaciones entre tablas
- Estadísticas de uso
- Verificación de existencia

USO:
    cd backend
    py scripts/identificar_tablas_crm.py
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from sqlalchemy import text, inspect

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Definición de tablas CRM
TABLAS_CRM = {
    'CORE': ['clientes'],
    'ATENCION': ['tickets'],
    'COMUNICACION': [
        'conversaciones_whatsapp',
        'comunicaciones_email',
        'notificaciones'
    ],
    'IA': ['conversaciones_ai'],
    'VENTAS': ['prestamos'],
    'COBRANZA': ['pagos']
}

TABLAS_CATALOGO = [
    'concesionarios',
    'analistas',
    'modelos_vehiculos',
    'users',
    'notificacion_plantillas'
]


def verificar_tabla_existe(db, tabla: str) -> bool:
    """Verifica si una tabla existe en la base de datos"""
    try:
        inspector = inspect(db.bind)
        return tabla in inspector.get_table_names()
    except Exception:
        return False


def obtener_total_registros(db, tabla: str) -> int:
    """Obtiene el total de registros en una tabla"""
    try:
        result = db.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
        return result.scalar() or 0
    except Exception:
        return 0


def obtener_foreign_keys(db, tabla: str) -> List[Dict]:
    """Obtiene las foreign keys de una tabla"""
    try:
        inspector = inspect(db.bind)
        fks = inspector.get_foreign_keys(tabla)
        return fks
    except Exception:
        return []


def generar_reporte_tablas_principales(db):
    """Genera reporte de tablas principales de CRM"""
    logger.info("=" * 60)
    logger.info("📊 TABLAS PRINCIPALES DE CRM")
    logger.info("=" * 60)
    logger.info("")
    
    for categoria, tablas in TABLAS_CRM.items():
        logger.info(f"📁 {categoria}:")
        for tabla in tablas:
            existe = verificar_tabla_existe(db, tabla)
            if existe:
                total = obtener_total_registros(db, tabla)
                logger.info(f"   ✅ {tabla:30} - {total:>8} registros")
            else:
                logger.info(f"   ❌ {tabla:30} - NO EXISTE")
        logger.info("")


def generar_reporte_relaciones(db):
    """Genera reporte de relaciones entre tablas CRM"""
    logger.info("=" * 60)
    logger.info("🔗 RELACIONES ENTRE TABLAS CRM (Foreign Keys)")
    logger.info("=" * 60)
    logger.info("")
    
    todas_tablas = []
    for tablas in TABLAS_CRM.values():
        todas_tablas.extend(tablas)
    
    relaciones_encontradas = []
    
    for tabla in todas_tablas:
        if not verificar_tabla_existe(db, tabla):
            continue
            
        fks = obtener_foreign_keys(db, tabla)
        for fk in fks:
            tabla_destino = fk['referred_table']
            columnas = ', '.join(fk['constrained_columns'])
            columnas_ref = ', '.join(fk['referred_columns'])
            
            relaciones_encontradas.append({
                'origen': tabla,
                'destino': tabla_destino,
                'columnas': columnas,
                'columnas_ref': columnas_ref
            })
    
    if relaciones_encontradas:
        logger.info(f"{'Tabla Origen':<25} {'→':^5} {'Tabla Destino':<25} {'Columnas':<30}")
        logger.info("-" * 90)
        for rel in relaciones_encontradas:
            logger.info(
                f"{rel['origen']:<25} {'→':^5} {rel['destino']:<25} "
                f"{rel['columnas']} → {rel['columnas_ref']}"
            )
    else:
        logger.info("   No se encontraron relaciones")
    
    logger.info("")


def generar_reporte_estadisticas(db):
    """Genera reporte de estadísticas de uso"""
    logger.info("=" * 60)
    logger.info("📈 ESTADÍSTICAS DE USO DE CRM")
    logger.info("=" * 60)
    logger.info("")
    
    # Estadísticas generales
    estadisticas = []
    
    for categoria, tablas in TABLAS_CRM.items():
        for tabla in tablas:
            if verificar_tabla_existe(db, tabla):
                total = obtener_total_registros(db, tabla)
                estadisticas.append({
                    'categoria': categoria,
                    'tabla': tabla,
                    'total': total
                })
    
    if estadisticas:
        logger.info(f"{'Categoría':<15} {'Tabla':<30} {'Total Registros':>15}")
        logger.info("-" * 60)
        for stat in estadisticas:
            logger.info(f"{stat['categoria']:<15} {stat['tabla']:<30} {stat['total']:>15}")
    
    logger.info("")
    
    # Estadísticas de actividad reciente (últimos 30 días)
    logger.info("📅 ACTIVIDAD CRM (Últimos 30 días)")
    logger.info("-" * 60)
    
    queries_actividad = [
        ("Tickets creados", "tickets", "creado_en"),
        ("Conversaciones WhatsApp", "conversaciones_whatsapp", "timestamp"),
        ("Comunicaciones Email", "comunicaciones_email", "timestamp"),
        ("Conversaciones IA", "conversaciones_ai", "creado_en"),
        ("Notificaciones enviadas", "notificaciones", "enviada_en"),
    ]
    
    for nombre, tabla, campo_fecha in queries_actividad:
        if not verificar_tabla_existe(db, tabla):
            continue
        
        try:
            query = text(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT cliente_id) as clientes_unicos
                FROM {tabla}
                WHERE {campo_fecha} >= NOW() - INTERVAL '30 days'
            """)
            result = db.execute(query)
            row = result.fetchone()
            
            if row:
                logger.info(
                    f"   {nombre:<30} - Total: {row[0]:>6}, "
                    f"Clientes únicos: {row[1]:>6}"
                )
        except Exception as e:
            logger.warning(f"   ⚠️  No se pudo obtener estadísticas de {tabla}: {e}")
    
    logger.info("")


def generar_reporte_tablas_catalogo(db):
    """Genera reporte de tablas de catálogo relacionadas"""
    logger.info("=" * 60)
    logger.info("📋 TABLAS DE CATÁLOGO Y CONFIGURACIÓN")
    logger.info("=" * 60)
    logger.info("")
    
    for tabla in TABLAS_CATALOGO:
        existe = verificar_tabla_existe(db, tabla)
        if existe:
            total = obtener_total_registros(db, tabla)
            logger.info(f"   ✅ {tabla:30} - {total:>8} registros")
        else:
            logger.info(f"   ❌ {tabla:30} - NO EXISTE")
    
    logger.info("")


def generar_reporte_resumen(db):
    """Genera resumen ejecutivo"""
    logger.info("=" * 60)
    logger.info("📊 RESUMEN EJECUTIVO")
    logger.info("=" * 60)
    logger.info("")
    
    total_tablas = 0
    tablas_existentes = 0
    
    for categoria, tablas in TABLAS_CRM.items():
        for tabla in tablas:
            total_tablas += 1
            if verificar_tabla_existe(db, tabla):
                tablas_existentes += 1
    
    logger.info(f"   Total de tablas CRM definidas: {total_tablas}")
    logger.info(f"   Tablas existentes en BD: {tablas_existentes}")
    logger.info(f"   Tablas faltantes: {total_tablas - tablas_existentes}")
    logger.info("")
    
    if tablas_existentes == total_tablas:
        logger.info("   ✅ Todas las tablas CRM están presentes")
    else:
        logger.warning(f"   ⚠️  Faltan {total_tablas - tablas_existentes} tablas CRM")
    
    logger.info("")


def main():
    """Función principal"""
    db = SessionLocal()
    
    try:
        logger.info("")
        logger.info("=" * 60)
        logger.info("🔍 IDENTIFICACIÓN DE TABLAS CRM")
        logger.info("=" * 60)
        logger.info("")
        
        # Generar reportes
        generar_reporte_tablas_principales(db)
        generar_reporte_relaciones(db)
        generar_reporte_estadisticas(db)
        generar_reporte_tablas_catalogo(db)
        generar_reporte_resumen(db)
        
        logger.info("=" * 60)
        logger.info("✅ IDENTIFICACIÓN COMPLETA")
        logger.info("=" * 60)
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Error al generar reporte: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

