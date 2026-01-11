"""
Utilidades seguras para construcción de queries SQL
Previene SQL injection usando solo parámetros nombrados
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Result
from sqlalchemy.orm import Session


def build_safe_where_clause(conditions: List[str], params: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Construye una cláusula WHERE de forma segura usando solo parámetros nombrados.

    Args:
        conditions: Lista de condiciones SQL con parámetros nombrados (ej: "campo = :valor")
        params: Diccionario con los valores de los parámetros

    Returns:
        Tupla (where_clause, params_dict)

    Ejemplo:
        conditions = ["fecha >= :fecha_inicio", "activo = :activo"]
        params = {"fecha_inicio": date.today(), "activo": True}
        where_clause, final_params = build_safe_where_clause(conditions, params)
        # Resultado: ("fecha >= :fecha_inicio AND activo = :activo", params)
    """
    if not conditions:
        return "", params or {}

    where_clause = " AND ".join(conditions)
    return where_clause, params or {}


def execute_safe_query(
    db: Session,
    base_query: str,
    where_clause: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Result:
    """
    Ejecuta una query SQL de forma segura usando parámetros nombrados.

    Args:
        db: Sesión de base de datos
        base_query: Query base sin WHERE (ej: "SELECT * FROM tabla")
        where_clause: Cláusula WHERE construida con build_safe_where_clause
        params: Parámetros para bindparams

    Returns:
        Result de SQLAlchemy

    Ejemplo:
        result = execute_safe_query(
            db,
            "SELECT * FROM pagos",
            where_clause="fecha_pago >= :fecha_inicio AND activo = :activo",
            params={"fecha_inicio": date.today(), "activo": True}
        )
    """
    query = base_query
    if where_clause:
        query = f"{base_query} WHERE {where_clause}"

    return db.execute(text(query).bindparams(**(params or {})))


def validate_table_name(table_name: str, allowed_tables: List[str]) -> bool:
    """
    Valida que un nombre de tabla esté en la lista permitida.
    Previene SQL injection por nombres de tabla dinámicos.

    Args:
        table_name: Nombre de tabla a validar
        allowed_tables: Lista de tablas permitidas

    Returns:
        True si el nombre está permitido, False en caso contrario
    """
    if not table_name or not isinstance(table_name, str):
        return False

    # Remover espacios y convertir a minúsculas para comparación
    table_name_clean = table_name.strip().lower()

    # Validar que solo contenga caracteres alfanuméricos y guiones bajos
    if not table_name_clean.replace("_", "").isalnum():
        return False

    return table_name_clean in [t.lower() for t in allowed_tables]


def validate_column_name(column_name: str, allowed_columns: List[str]) -> bool:
    """
    Valida que un nombre de columna esté en la lista permitida.
    Previene SQL injection por nombres de columna dinámicos.

    Args:
        column_name: Nombre de columna a validar
        allowed_columns: Lista de columnas permitidas

    Returns:
        True si el nombre está permitido, False en caso contrario
    """
    if not column_name or not isinstance(column_name, str):
        return False

    # Remover espacios y convertir a minúsculas para comparación
    column_name_clean = column_name.strip().lower()

    # Validar que solo contenga caracteres alfanuméricos y guiones bajos
    if not column_name_clean.replace("_", "").isalnum():
        return False

    return column_name_clean in [c.lower() for c in allowed_columns]


def sanitize_table_name(table_name: str) -> str:
    """
    Sanitiza un nombre de tabla removiendo caracteres peligrosos.
    Solo permite caracteres alfanuméricos y guiones bajos.

    Args:
        table_name: Nombre de tabla a sanitizar

    Returns:
        Nombre sanitizado

    Raises:
        ValueError: Si el nombre contiene caracteres no permitidos
    """
    if not table_name or not isinstance(table_name, str):
        raise ValueError("Nombre de tabla inválido")

    # Remover espacios
    sanitized = table_name.strip()

    # Validar que solo contenga caracteres alfanuméricos y guiones bajos
    if not sanitized.replace("_", "").isalnum():
        raise ValueError(f"Nombre de tabla contiene caracteres no permitidos: {table_name}")

    return sanitized


def sanitize_column_name(column_name: str) -> str:
    """
    Sanitiza un nombre de columna removiendo caracteres peligrosos.
    Solo permite caracteres alfanuméricos y guiones bajos.

    Args:
        column_name: Nombre de columna a sanitizar

    Returns:
        Nombre sanitizado

    Raises:
        ValueError: Si el nombre contiene caracteres no permitidos
    """
    if not column_name or not isinstance(column_name, str):
        raise ValueError("Nombre de columna inválido")

    # Remover espacios
    sanitized = column_name.strip()

    # Validar que solo contenga caracteres alfanuméricos y guiones bajos
    if not sanitized.replace("_", "").isalnum():
        raise ValueError(f"Nombre de columna contiene caracteres no permitidos: {column_name}")

    return sanitized
