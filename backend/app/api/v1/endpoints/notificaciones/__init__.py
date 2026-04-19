"""Notificaciones: router FastAPI y helpers compartidos con notificaciones_tabs y pruebas."""

from .routes import (
    _format_item_texto_plantilla_por_defecto,
    _sustituir_variables,
    build_contexto_cobranza_para_item,
    build_prejudicial_items,
    contexto_cobranza_aplica_a_prestamo,
    get_notificaciones_envios_config,
    get_notificaciones_tabs_data,
    get_plantilla_asunto_cuerpo,
    plantilla_usa_variables_cobranza,
    router,
)

__all__ = [
    "_format_item_texto_plantilla_por_defecto",
    "_sustituir_variables",
    "build_contexto_cobranza_para_item",
    "build_prejudicial_items",
    "contexto_cobranza_aplica_a_prestamo",
    "get_notificaciones_envios_config",
    "get_notificaciones_tabs_data",
    "get_plantilla_asunto_cuerpo",
    "plantilla_usa_variables_cobranza",
    "router",
]
