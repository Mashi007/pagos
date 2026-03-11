"""
Motor de sustitución para plantillas de cobranza.
Soporta variables {{TABLA.CAMPO}} y bloque de iteración {{#CUOTAS.VENCIMIENTOS}}...{{/CUOTAS.VENCIMIENTOS}}.
"""
import re
from datetime import date
from typing import Any


def _format_fecha(value: Any) -> str:
    """Formatea fecha para mostrar en carta (dd/mm/yyyy)."""
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str):
        try:
            d = date.fromisoformat(value[:10])
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(value)
    return str(value)


def _format_monto(value: Any) -> str:
    """Formatea monto numérico (2 decimales, separador de miles)."""
    if value is None:
        return "0.00"
    try:
        n = float(value)
        return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(value)


def render_plantilla_cobranza(texto: str, contexto: dict) -> str:
    """
    Renderiza una plantilla de cobranza con:
    - Variables {{TABLA.CAMPO}} (ej. {{CLIENTES.NOMBRE_COMPLETO}}, {{PRESTAMOS.ID}}, {{FECHA_CARTA}}).
    - Bloque {{#CUOTAS.VENCIMIENTOS}} ... {{/CUOTAS.VENCIMIENTOS}} que se repite por cada cuota vencida.
      Dentro del bloque: {{CUOTA.NUMERO}}, {{CUOTA.FECHA_VENCIMIENTO}}, {{CUOTA.MONTO}}.

    contexto esperado:
      - CLIENTES.TRATAMIENTO, CLIENTES.NOMBRE_COMPLETO
      - PRESTAMOS.ID
      - FECHA_CARTA (date o str iso)
      - CUOTAS.VENCIMIENTOS: lista de dicts con keys numero (o numero_cuota), fecha_vencimiento, monto
    """
    if not texto:
        return ""

    result = texto

    # 1) Reemplazar variables simples {{TABLA.CAMPO}} o {{FECHA_CARTA}}
    # Buscar todos los {{...}} que no son bloques # o /
    pattern_simple = re.compile(r"\{\{([^#/].*?)\}\}")
    for m in pattern_simple.finditer(result):
        key = m.group(1).strip()
        value = contexto.get(key)
        if value is None and "." in key:
            # Permitir clave con punto en contexto plano (ej. FECHA_CARTA)
            value = contexto.get(key)
        if value is not None:
            if "FECHA" in key.upper() or "FECHA" in key:
                value = _format_fecha(value)
            result = result.replace(m.group(0), str(value))
        else:
            result = result.replace(m.group(0), "")

    # 2) Bloque {{#CUOTAS.VENCIMIENTOS}} ... {{/CUOTAS.VENCIMIENTOS}}
    block_start = "{{#CUOTAS.VENCIMIENTOS}}"
    block_end = "{{/CUOTAS.VENCIMIENTOS}}"
    if block_start in result and block_end in result:
        idx_start = result.index(block_start)
        idx_end = result.index(block_end)
        if idx_end > idx_start:
            prefix = result[:idx_start]
            suffix = result[idx_end + len(block_end):]
            template_block = result[idx_start + len(block_start):idx_end]
            cuotas = contexto.get("CUOTAS.VENCIMIENTOS") or contexto.get("cuotas_vencidas") or []
            parts = []
            for c in cuotas:
                if isinstance(c, dict):
                    num = c.get("numero") or c.get("numero_cuota") or ""
                    fv = c.get("fecha_vencimiento")
                    monto = c.get("monto") or c.get("monto_cuota")
                else:
                    num = getattr(c, "numero_cuota", "") or getattr(c, "numero", "")
                    fv = getattr(c, "fecha_vencimiento", None)
                    monto = getattr(c, "monto", None) or getattr(c, "monto_cuota", None)
                block_rendered = template_block
                block_rendered = block_rendered.replace("{{CUOTA.NUMERO}}", str(num))
                block_rendered = block_rendered.replace("{{CUOTA.FECHA_VENCIMIENTO}}", _format_fecha(fv))
                block_rendered = block_rendered.replace("{{CUOTA.MONTO}}", _format_monto(monto))
                parts.append(block_rendered)
            result = prefix + "\n".join(parts) + suffix

    # 3) Pasar de nuevo por variables por si quedaron dentro de bloques ya expandidos
    for key, value in contexto.items():
        if key in ("CUOTAS.VENCIMIENTOS", "cuotas_vencidas") or isinstance(value, list):
            continue
        token = "{{" + key + "}}"
        if token in result:
            if "FECHA" in key.upper():
                value = _format_fecha(value)
            result = result.replace(token, str(value) if value is not None else "")

    return result


def construir_contexto_cobranza(
    cliente_nombres: str,
    prestamo_id: int,
    cuotas_vencidas: list,
    tratamiento: str = "Sr/Sra.",
    fecha_carta: date | None = None,
) -> dict:
    """
    Construye el diccionario de contexto para render_plantilla_cobranza.
    cuotas_vencidas: lista de dicts con numero_cuota, fecha_vencimiento, monto (o objetos Cuota).
    """
    from datetime import date as date_type
    f = fecha_carta or date_type.today()
    lista = []
    for c in cuotas_vencidas:
        if isinstance(c, dict):
            lista.append({
                "numero": c.get("numero_cuota") or c.get("numero"),
                "fecha_vencimiento": c.get("fecha_vencimiento"),
                "monto": c.get("monto") or c.get("monto_cuota"),
            })
        else:
            lista.append({
                "numero": getattr(c, "numero_cuota", None),
                "fecha_vencimiento": getattr(c, "fecha_vencimiento", None),
                "monto": float(getattr(c, "monto", 0) or getattr(c, "monto_cuota", 0)) if hasattr(c, "monto") or hasattr(c, "monto_cuota") else None,
            })
    return {
        "CLIENTES.TRATAMIENTO": tratamiento,
        "CLIENTES.NOMBRE_COMPLETO": cliente_nombres or "",
        "PRESTAMOS.ID": prestamo_id,
        "FECHA_CARTA": f,
        "CUOTAS.VENCIMIENTOS": lista,
        "cuotas_vencidas": lista,
    }
