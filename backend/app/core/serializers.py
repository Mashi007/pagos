"""
Módulo centralizado para serialización y conversiones comunes.
Centraliza funciones de formato que se usan repetidamente en múltiples endpoints.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional


def to_float(value: Any) -> Optional[float]:
    """
    Convierte un valor a float de forma segura.
    
    Args:
        value: Valor a convertir (Decimal, int, float, str, None, etc.)
    
    Returns:
        float o None si no se puede convertir
    """
    if value is None:
        return None
    
    if isinstance(value, float):
        return value
    
    if isinstance(value, Decimal):
        return float(value)
    
    if isinstance(value, (int, str)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    
    return None


def format_date_iso(value: Any) -> Optional[str]:
    """
    Convierte una fecha a formato ISO (YYYY-MM-DD).
    
    Args:
        value: Valor a convertir (date, datetime, str, None, etc.)
    
    Returns:
        String en formato ISO o None
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value.date().isoformat()
    
    if isinstance(value, date):
        return value.isoformat()
    
    if isinstance(value, str):
        # Asumir que es ISO o parseable
        return value
    
    return None


def format_datetime_iso(value: Any) -> Optional[str]:
    """
    Convierte un datetime a formato ISO con hora.
    
    Args:
        value: Valor a convertir (datetime, date, str, None, etc.)
    
    Returns:
        String en formato ISO o None
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value.isoformat()
    
    if isinstance(value, date):
        # Convertir date a datetime a las 00:00:00
        dt = datetime.combine(value, datetime.min.time())
        return dt.isoformat()
    
    if isinstance(value, str):
        return value
    
    return None


def format_decimal(value: Any, places: int = 2) -> Optional[float]:
    """
    Convierte Decimal a float con redondeo específico.
    
    Args:
        value: Valor a convertir
        places: Decimales para redondeo (por defecto 2)
    
    Returns:
        float o None
    """
    if value is None:
        return None
    
    try:
        if isinstance(value, Decimal):
            return float(round(value, places))
        return to_float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def safe_json_loads(value: Any, default: Any = None) -> Any:
    """
    Parsea JSON de forma segura.
    
    Args:
        value: String JSON a parsear
        default: Valor por defecto si falla
    
    Returns:
        Objeto parseado o default
    """
    import json
    
    if not value:
        return default
    
    try:
        if isinstance(value, str):
            return json.loads(value)
        return value
    except (json.JSONDecodeError, TypeError):
        return default


def coalesce(*values) -> Any:
    """
    Retorna el primer valor no None.
    
    Args:
        *values: Valores a evaluar
    
    Returns:
        Primer valor no None, o None si todos son None
    """
    for v in values:
        if v is not None:
            return v
    return None
