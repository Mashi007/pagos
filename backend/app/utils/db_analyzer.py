"""
Analizador de Base de Datos
Obtiene información sobre tamaño, tablas, índices y campos usados
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_database_size(db: Session) -> Dict:
    """
    Obtener tamaño total de la base de datos
    
    Returns:
        Dict con información de tamaño de BD
    """
    try:
        query = text("""
            SELECT 
                pg_database.datname,
                pg_size_pretty(pg_database_size(pg_database.datname)) AS size_pretty,
                pg_database_size(pg_database.datname) AS size_bytes
            FROM pg_database
            WHERE datname = current_database()
        """)
        
        result = db.execute(query).fetchone()
        
        if result:
            return {
                "database_name": result[0],
                "size_pretty": result[1],
                "size_bytes": result[2],
                "size_mb": round(result[2] / (1024 * 1024), 2),
                "size_gb": round(result[2] / (1024 * 1024 * 1024), 2),
            }
        return {}
    except Exception as e:
        logger.error(f"Error obteniendo tamaño de BD: {e}")
        return {}


def get_table_sizes(db: Session, limit: int = 20) -> List[Dict]:
    """
    Obtener tamaños de las tablas más grandes
    
    Args:
        limit: Número máximo de tablas a retornar
        
    Returns:
        Lista de dicts con información de tablas
    """
    try:
        query = text("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size_pretty,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes,
                pg_relation_size(schemaname||'.'||tablename) AS table_size_bytes,
                pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename) AS indexes_size_bytes
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {"limit": limit}).fetchall()
        
        tables = []
        for row in results:
            tables.append({
                "schema": row[0],
                "table_name": row[1],
                "size_pretty": row[2],
                "size_bytes": row[3],
                "table_size_mb": round(row[4] / (1024 * 1024), 2),
                "indexes_size_mb": round(row[5] / (1024 * 1024), 2) if row[5] else 0,
                "total_size_mb": round(row[3] / (1024 * 1024), 2),
            })
        
        return tables
    except Exception as e:
        logger.error(f"Error obteniendo tamaños de tablas: {e}")
        return []


def get_table_columns(db: Session, table_name: str) -> List[Dict]:
    """
    Obtener columnas de una tabla específica
    
    Args:
        table_name: Nombre de la tabla
        
    Returns:
        Lista de dicts con información de columnas
    """
    try:
        query = text("""
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' 
              AND table_name = :table_name
            ORDER BY ordinal_position
        """)
        
        results = db.execute(query, {"table_name": table_name}).fetchall()
        
        columns = []
        for row in results:
            columns.append({
                "column_name": row[0],
                "data_type": row[1],
                "max_length": row[2],
                "nullable": row[3] == "YES",
                "default": row[4],
            })
        
        return columns
    except Exception as e:
        logger.error(f"Error obteniendo columnas de tabla {table_name}: {e}")
        return []


def get_indexes_for_table(db: Session, table_name: str) -> List[Dict]:
    """
    Obtener índices de una tabla específica
    
    Args:
        table_name: Nombre de la tabla
        
    Returns:
        Lista de dicts con información de índices
    """
    try:
        query = text("""
            SELECT 
                indexname,
                indexdef,
                pg_size_pretty(pg_relation_size(indexname::regclass)) AS size_pretty,
                pg_relation_size(indexname::regclass) AS size_bytes
            FROM pg_indexes
            WHERE schemaname = 'public' 
              AND tablename = :table_name
            ORDER BY pg_relation_size(indexname::regclass) DESC NULLS LAST
        """)
        
        results = db.execute(query, {"table_name": table_name}).fetchall()
        
        indexes = []
        for row in results:
            indexes.append({
                "index_name": row[0],
                "definition": row[1],
                "size_pretty": row[2] or "0 bytes",
                "size_bytes": row[3] or 0,
                "size_mb": round((row[3] or 0) / (1024 * 1024), 2),
            })
        
        return indexes
    except Exception as e:
        logger.error(f"Error obteniendo índices de tabla {table_name}: {e}")
        return []


def analyze_query_tables_columns(query_sql: Optional[str]) -> Dict:
    """
    Analizar una query SQL para extraer tablas y columnas usadas
    
    Args:
        query_sql: SQL de la query (puede ser None)
        
    Returns:
        Dict con tablas y columnas detectadas
    """
    if not query_sql:
        return {"tables": [], "columns": []}
    
    # Tablas comunes del sistema
    common_tables = [
        "prestamos", "cuotas", "pagos", "clientes", "pagos_staging",
        "users", "notificaciones", "aprobaciones", "auditorias"
    ]
    
    # Columnas comunes
    common_columns = [
        "fecha_aprobacion", "fecha_registro", "fecha_vencimiento", "fecha_pago",
        "estado", "cedula", "total_financiamiento", "monto_cuota", "total_pagado",
        "capital_pendiente", "interes_pendiente", "monto_mora", "analista",
        "concesionario", "modelo_vehiculo", "producto"
    ]
    
    query_lower = query_sql.lower()
    
    # Detectar tablas
    tables_found = []
    for table in common_tables:
        if table in query_lower:
            tables_found.append(table)
    
    # Detectar columnas
    columns_found = []
    for column in common_columns:
        if column in query_lower:
            columns_found.append(column)
    
    return {
        "tables": tables_found,
        "columns": columns_found,
        "query_preview": query_sql[:200] if query_sql else None,
    }


def get_database_info(db: Session) -> Dict:
    """
    Obtener información completa de la base de datos
    
    Returns:
        Dict con información completa de BD
    """
    try:
        db_size = get_database_size(db)
        table_sizes = get_table_sizes(db, limit=10)
        
        # Calcular total de tablas
        count_query = text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        total_tables = db.execute(count_query).scalar() or 0
        
        # Calcular total de índices
        index_count_query = text("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE schemaname = 'public'
        """)
        total_indexes = db.execute(index_count_query).scalar() or 0
        
        return {
            "database": db_size,
            "total_tables": total_tables,
            "total_indexes": total_indexes,
            "largest_tables": table_sizes,
            "summary": {
                "total_size_mb": sum(t.get("total_size_mb", 0) for t in table_sizes),
                "largest_table": table_sizes[0] if table_sizes else None,
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo información de BD: {e}")
        return {}

