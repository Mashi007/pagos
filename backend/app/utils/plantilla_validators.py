"""
Utilidades de validación y sanitización para plantillas de notificaciones
"""

import re
from html import escape
from typing import List, Optional

from fastapi import HTTPException

# Intentar importar bleach para sanitización HTML robusta
try:
    import bleach

    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False

# Tipos permitidos de plantillas
TIPOS_PERMITIDOS = [
    "PAGO_5_DIAS_ANTES",
    "PAGO_3_DIAS_ANTES",
    "PAGO_1_DIA_ANTES",
    "PAGO_DIA_0",
    "PAGO_1_DIA_ATRASADO",
    "PAGO_3_DIAS_ATRASADO",
    "PAGO_5_DIAS_ATRASADO",
    "PREJUDICIAL",
]

# Variables requeridas por tipo de plantilla
REQUERIDAS_POR_TIPO: dict[str, List[str]] = {
    "PAGO_5_DIAS_ANTES": ["nombre", "monto", "fecha_vencimiento"],
    "PAGO_3_DIAS_ANTES": ["nombre", "monto", "fecha_vencimiento"],
    "PAGO_1_DIA_ANTES": ["nombre", "monto", "fecha_vencimiento"],
    "PAGO_DIA_0": ["nombre", "monto", "fecha_vencimiento"],
    "PAGO_1_DIA_ATRASADO": ["nombre", "monto", "fecha_vencimiento", "dias_atraso"],
    "PAGO_3_DIAS_ATRASADO": ["nombre", "monto", "fecha_vencimiento", "dias_atraso"],
    "PAGO_5_DIAS_ATRASADO": ["nombre", "monto", "fecha_vencimiento", "dias_atraso"],
    "PREJUDICIAL": ["nombre", "monto", "fecha_vencimiento", "dias_atraso"],
}

# Tags HTML permitidos para sanitización
HTML_TAGS_PERMITIDOS = ["p", "br", "strong", "em", "b", "i", "u", "ul", "ol", "li", "a", "div", "span"]

# Atributos permitidos para tags específicos
HTML_ATRIBUTOS_PERMITIDOS = {
    "a": ["href", "title", "target"],
    "div": ["class"],
    "span": ["class"],
}


def validar_tipo_plantilla(tipo: str) -> None:
    """
    Valida que el tipo de plantilla esté en la lista blanca de tipos permitidos.

    Args:
        tipo: Tipo de plantilla a validar

    Raises:
        HTTPException: Si el tipo no está permitido
    """
    if tipo not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de plantilla no permitido: '{tipo}'. Tipos permitidos: {', '.join(TIPOS_PERMITIDOS)}",
        )


def sanitizar_html(texto: str, permitir_html: bool = True) -> str:
    """
    Sanitiza HTML permitiendo solo tags y atributos seguros.

    Protege las variables {{variable}} y permite solo HTML seguro.
    Usa bleach si está disponible para sanitización robusta, sino usa método básico.

    Args:
        texto: Texto que puede contener HTML
        permitir_html: Si True, permite HTML seguro. Si False, escapa todo HTML.

    Returns:
        Texto sanitizado
    """
    if not texto:
        return texto

    if not permitir_html:
        # Escapar todo HTML
        return escape(texto)

    # Primero, proteger las variables {{variable}} para que no sean afectadas
    variables_protegidas = {}
    variable_pattern = r"\{\{([^}]+)\}\}"

    # Encontrar todas las variables y reemplazarlas con placeholders
    texto_procesado = texto
    idx = 0
    for match in re.finditer(variable_pattern, texto):
        placeholder = f"__VARIABLE_PROTECTED_{idx}__"
        variables_protegidas[placeholder] = match.group(0)
        texto_procesado = texto_procesado.replace(match.group(0), placeholder, 1)
        idx += 1

    # Usar bleach si está disponible para sanitización robusta
    if BLEACH_AVAILABLE:
        # Configurar bleach con tags y atributos permitidos
        tags_permitidos = HTML_TAGS_PERMITIDOS
        atributos_permitidos = {
            "a": ["href", "title", "target"],
            "div": ["class"],
            "span": ["class"],
        }

        # Sanitizar con bleach
        texto_sanitizado = bleach.clean(
            texto_procesado,
            tags=tags_permitidos,
            attributes=atributos_permitidos,
            protocols=["http", "https", "mailto"],  # Solo protocolos seguros para href
            strip=True,  # Eliminar tags no permitidos
        )
    else:
        # Fallback a método básico si bleach no está disponible
        # Escapar todo HTML primero
        texto_sanitizado = escape(texto_procesado)

        # Permitir tags seguros básicos (solo tags de formato, no scripts ni estilos)
        for tag in HTML_TAGS_PERMITIDOS:
            # Permitir tags de apertura con atributos básicos
            texto_sanitizado = re.sub(
                rf"&lt;({tag})(\s+[^&]*)?&gt;",
                lambda m: _sanitizar_tag_abierto(tag, m.group(2) if m.group(2) else ""),
                texto_sanitizado,
                flags=re.IGNORECASE,
            )
            # Permitir tags de cierre
            texto_sanitizado = re.sub(
                rf"&lt;/({tag})&gt;",
                rf"</\1>",
                texto_sanitizado,
                flags=re.IGNORECASE,
            )

    # Restaurar variables protegidas al final
    for placeholder, variable in variables_protegidas.items():
        texto_sanitizado = texto_sanitizado.replace(placeholder, variable)

    return texto_sanitizado


def _sanitizar_tag_abierto(tag: str, atributos: str) -> str:
    """Sanitiza atributos de un tag abierto."""
    if tag == "a":
        return _limpiar_atributos_a(atributos)
    elif tag in ["div", "span"]:
        # Permitir solo atributo class
        class_match = re.search(r'class=["\']([^"\']+)["\']', atributos, re.IGNORECASE)
        if class_match:
            class_value = escape(class_match.group(1))
            return f'<{tag} class="{class_value}">'
        return f"<{tag}>"
    else:
        # Para otros tags, no permitir atributos
        return f"<{tag}>"


def _limpiar_atributos_a(atributos: str) -> str:
    """Limpia atributos de tags <a> permitiendo solo href, title, target seguros."""
    atributos_permitidos = []
    href_match = re.search(r'href=["\']([^"\']+)["\']', atributos, re.IGNORECASE)
    title_match = re.search(r'title=["\']([^"\']+)["\']', atributos, re.IGNORECASE)
    target_match = re.search(r'target=["\']([^"\']+)["\']', atributos, re.IGNORECASE)

    if href_match:
        href = href_match.group(1)
        # Validar que href sea seguro (http/https o mailto)
        if re.match(r"^(https?://|mailto:|#)", href, re.IGNORECASE):
            atributos_permitidos.append(f'href="{href}"')

    if title_match:
        title = escape(title_match.group(1))
        atributos_permitidos.append(f'title="{title}"')

    if target_match:
        target = target_match.group(1)
        if target in ["_blank", "_self", "_parent", "_top"]:
            atributos_permitidos.append(f'target="{target}"')

    attrs_str = " ".join(atributos_permitidos)
    return f"<a {attrs_str}>" if attrs_str else "<a>"


def validar_variables_obligatorias(tipo: str, asunto: str, cuerpo: str) -> None:
    """
    Valida que la plantilla contenga todas las variables obligatorias para su tipo.

    Args:
        tipo: Tipo de plantilla
        asunto: Asunto de la plantilla
        cuerpo: Cuerpo de la plantilla

    Raises:
        HTTPException: Si faltan variables obligatorias
    """
    if tipo not in REQUERIDAS_POR_TIPO:
        # Si el tipo no está en la lista, no validamos (puede ser un tipo nuevo)
        return

    requeridas = REQUERIDAS_POR_TIPO[tipo]
    texto_completo = f"{asunto} {cuerpo}"

    faltantes = []
    for variable in requeridas:
        # Buscar variable en formato {{variable}}
        # ✅ Construir patrón sin backslashes en expresión f-string
        patron = r"\{\{" + re.escape(variable) + r"\}\}"
        if not re.search(patron, texto_completo):
            faltantes.append(variable)

    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Para el tipo '{tipo}' faltan variables obligatorias: {', '.join(faltantes)}. "
            f"Variables requeridas: {', '.join(requeridas)}",
        )


def validar_y_sanitizar_plantilla(
    tipo: str,
    asunto: str,
    cuerpo: str,
    descripcion: Optional[str] = None,
    sanitizar_html_enabled: bool = True,
) -> tuple[str, str, Optional[str]]:
    """
    Valida y sanitiza todos los campos de una plantilla.

    Args:
        tipo: Tipo de plantilla
        asunto: Asunto de la plantilla
        cuerpo: Cuerpo de la plantilla
        descripcion: Descripción opcional
        sanitizar_html_enabled: Si True, sanitiza HTML. Si False, solo valida.

    Returns:
        Tupla con (asunto_sanitizado, cuerpo_sanitizado, descripcion_sanitizada)

    Raises:
        HTTPException: Si hay errores de validación
    """
    # Validar tipo
    validar_tipo_plantilla(tipo)

    # Sanitizar campos de texto
    asunto_sanitizado = sanitizar_html(asunto, permitir_html=sanitizar_html_enabled)
    cuerpo_sanitizado = sanitizar_html(cuerpo, permitir_html=sanitizar_html_enabled)
    descripcion_sanitizada = sanitizar_html(descripcion, permitir_html=sanitizar_html_enabled) if descripcion else None

    # Validar variables obligatorias
    validar_variables_obligatorias(tipo, asunto_sanitizado, cuerpo_sanitizado)

    return asunto_sanitizado, cuerpo_sanitizado, descripcion_sanitizada
