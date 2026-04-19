"""Clientes: router y utilidades compartidas con importación desde Drive / candidatos."""

from .routes import (
    _cedula_clave_comparacion_clientes,
    _expr_cedula_normalizada_sql,
    _normalizar_cedula_carga_masiva,
    _normalize_for_duplicate,
    create_cliente_from_payload,
    router,
)

__all__ = [
    "_cedula_clave_comparacion_clientes",
    "_expr_cedula_normalizada_sql",
    "_normalizar_cedula_carga_masiva",
    "_normalize_for_duplicate",
    "create_cliente_from_payload",
    "router",
]
