"""
Motor de sustitucion para plantillas de cobranza.
Soporta variables {{TABLA.CAMPO}}, bloque {{#CUOTAS.VENCIMIENTOS}} y variable unica {{TABLA_CUOTAS_PENDIENTES}}.
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
    """Formatea monto numerico (2 decimales, separador de miles)."""
    if value is None:
        return "0.00"
    try:
        n = float(value)
        return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(value)


# Estilo HTML por defecto para tabla de cuotas (variable unica en el cuerpo).
_TABLA_CUOTAS_HTML_HEADER = """<table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; font-family:Arial, sans-serif; font-size:13px;">
  <tr style="background-color:#1a2744;">
    <th width="40" style="padding:10px 14px; text-align:left; color:#ffffff; font-size:11px; letter-spacing:1px; text-transform:uppercase; font-weight:bold;">#</th>
    <th style="padding:10px 14px; text-align:left; color:#ffffff; font-size:11px; letter-spacing:1px; text-transform:uppercase; font-weight:bold;">Vencimiento</th>
    <th style="padding:10px 14px; text-align:right; color:#e87722; font-size:11px; letter-spacing:1px; text-transform:uppercase; font-weight:bold;">Monto</th>
  </tr>
"""
_TABLA_CUOTAS_HTML_ROW_ODD = "  <tr style=\"background-color:#f7f9fc;\"><td style=\"padding:9px 14px; color:#888888; border-bottom:1px solid #e8ecf0;\">{numero}</td><td style=\"padding:9px 14px; color:#1a2744; border-bottom:1px solid #e8ecf0;\">{fecha}</td><td style=\"padding:9px 14px; text-align:right; color:#1a2744; font-weight:bold; border-bottom:1px solid #e8ecf0;\">$ {monto}</td></tr>\n"
_TABLA_CUOTAS_HTML_ROW_EVEN = "  <tr style=\"background-color:#ffffff;\"><td style=\"padding:9px 14px; color:#888888; border-bottom:1px solid #e8ecf0;\">{numero}</td><td style=\"padding:9px 14px; color:#1a2744; border-bottom:1px solid #e8ecf0;\">{fecha}</td><td style=\"padding:9px 14px; text-align:right; color:#1a2744; font-weight:bold; border-bottom:1px solid #e8ecf0;\">$ {monto}</td></tr>\n"
_TABLA_CUOTAS_HTML_FOOTER = """  <tr style="background-color:#1a2744;">
    <td colspan="2" style="padding:11px 14px; color:#ffffff; font-size:12px; font-weight:bold; text-transform:uppercase; letter-spacing:1px;">Total Adeudado</td>
    <td style="padding:11px 14px; text-align:right; color:#e87722; font-size:15px; font-weight:bold;">$ {total}</td>
  </tr>
</table>"""


def _build_tabla_cuotas_pendientes_html(contexto: dict) -> str:
    """Genera la tabla HTML completa de cuotas pendientes con formato por defecto."""
    cuotas = contexto.get("CUOTAS.VENCIMIENTOS") or contexto.get("cuotas_vencidas") or []
    total = contexto.get("TOTAL_ADEUDADO")
    if total is None:
        total_num = 0
        for c in cuotas:
            m = c.get("monto") if isinstance(c, dict) else getattr(c, "monto", None) or getattr(c, "monto_cuota", 0)
            try:
                total_num += float(m)
            except (TypeError, ValueError):
                pass
        total = _format_monto(total_num)
    else:
        total = _format_monto(total) if not isinstance(total, str) else total
    parts = [_TABLA_CUOTAS_HTML_HEADER]
    for i, c in enumerate(cuotas):
        if isinstance(c, dict):
            num = c.get("numero") or c.get("numero_cuota") or ""
            fv = _format_fecha(c.get("fecha_vencimiento"))
            monto = _format_monto(c.get("monto") or c.get("monto_cuota"))
        else:
            num = getattr(c, "numero_cuota", "") or getattr(c, "numero", "")
            fv = _format_fecha(getattr(c, "fecha_vencimiento", None))
            monto = _format_monto(getattr(c, "monto", None) or getattr(c, "monto_cuota", None))
        row_tpl = _TABLA_CUOTAS_HTML_ROW_ODD if i % 2 == 0 else _TABLA_CUOTAS_HTML_ROW_EVEN
        parts.append(row_tpl.format(numero=num, fecha=fv, monto=monto))
    parts.append(_TABLA_CUOTAS_HTML_FOOTER.format(total=total))
    return "".join(parts)


def render_plantilla_cobranza(texto: str, contexto: dict) -> str:
    """
    Renderiza una plantilla de cobranza con:
    - Variables {{TABLA.CAMPO}}, {{IDPRESTAMO}}, {{NUMEROCORRELATIVO}}, {{TOTAL_ADEUDADO}}.
    - Variable unica {{TABLA_CUOTAS_PENDIENTES}}: reemplazo por tabla HTML completa (cuotas + total).
    - Bloque {{#CUOTAS.VENCIMIENTOS}} ... {{/CUOTAS.VENCIMIENTOS}} (opcional).
    """
    if not texto:
        return ""

    result = texto

    # 0) Variable unica: tabla HTML completa de cuotas pendientes
    if "{{TABLA_CUOTAS_PENDIENTES}}" in result:
        result = result.replace("{{TABLA_CUOTAS_PENDIENTES}}", _build_tabla_cuotas_pendientes_html(contexto))

    # 1) Bloque {{#CUOTAS.VENCIMIENTOS}} ... {{/CUOTAS.VENCIMIENTOS}}
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

    # 2) Reemplazar variables simples desde contexto
    for key, value in list(contexto.items()):
        if key in ("CUOTAS.VENCIMIENTOS", "cuotas_vencidas") or isinstance(value, list):
            continue
        token = "{{" + key + "}}"
        if token not in result:
            continue
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
    logo_url: str | None = None,
    cedula: str | None = None,
    numero_correlativo: int = 1,
) -> dict:
    """
    Construye el diccionario de contexto para render_plantilla_cobranza.
    Incluye IDPRESTAMO, NUMEROCORRELATIVO, TOTAL_ADEUDADO y CUOTAS.VENCIMIENTOS.
    """
    from datetime import date as date_type
    try:
        from app.core.config import settings
        base = (logo_url or (getattr(settings, "FRONTEND_PUBLIC_URL", None) or "https://rapicredit.onrender.com/pagos")).rstrip("/")
    except Exception:
        base = (logo_url or "https://rapicredit.onrender.com/pagos").rstrip("/")
    url_logo = f"{base}/logos/rapicredit-public.png"

    f = fecha_carta or date_type.today()
    lista = []
    total_adeudado = 0
    for c in cuotas_vencidas:
        if isinstance(c, dict):
            m = c.get("monto") or c.get("monto_cuota") or 0
            lista.append({
                "numero": c.get("numero_cuota") or c.get("numero"),
                "fecha_vencimiento": c.get("fecha_vencimiento"),
                "monto": m,
            })
            try:
                total_adeudado += float(m)
            except (TypeError, ValueError):
                pass
        else:
            m = float(getattr(c, "monto", 0) or getattr(c, "monto_cuota", 0)) if (hasattr(c, "monto") or hasattr(c, "monto_cuota")) else 0
            lista.append({
                "numero": getattr(c, "numero_cuota", None),
                "fecha_vencimiento": getattr(c, "fecha_vencimiento", None),
                "monto": m,
            })
            total_adeudado += m

    return {
        "CLIENTES.TRATAMIENTO": tratamiento,
        "CLIENTES.NOMBRE_COMPLETO": cliente_nombres or "",
        "CLIENTES.CEDULA": cedula or "",
        "PRESTAMOS.ID": prestamo_id,
        "IDPRESTAMO": prestamo_id,
        "NUMEROCORRELATIVO": numero_correlativo,
        "TOTAL_ADEUDADO": _format_monto(total_adeudado),
        "FECHA_CARTA": f,
        "CUOTAS.VENCIMIENTOS": lista,
        "cuotas_vencidas": lista,
        "LOGO_URL": url_logo,
    }
