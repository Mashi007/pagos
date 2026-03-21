# -*- coding: utf-8 -*-
"""Parche: estado de cuota en recibos PDF (cuota_estado + recibo_pdf + wrapper + prestamos endpoint)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- cuota_estado.py ---
ce = ROOT / "backend" / "app" / "services" / "cuota_estado.py"
t = ce.read_text(encoding="utf-8")
anchor = (
    '    return clasificar_estado_cuota(\n'
    "        total_pagado, monto_cuota, fecha_vencimiento, fecha_referencia\n"
    "    )\n\n\n# SQL PostgreSQL"
)
insert = (
    '    return clasificar_estado_cuota(\n'
    "        total_pagado, monto_cuota, fecha_vencimiento, fecha_referencia\n"
    "    )\n\n\n"
    "def etiqueta_estado_cuota(codigo: str) -> str:\n"
    '    """Texto para UI/PDF (misma nomenclatura que la tabla de amortizacion en frontend)."""\n'
    '    c = (codigo or "").strip().upper()\n'
    "    labels = {\n"
    '        "PENDIENTE": "Pendiente",\n'
    '        "PARCIAL": "Pendiente parcial",\n'
    '        "VENCIDO": "Vencido (1-91 d)",\n'
    '        "MORA": "Mora (92+ d)",\n'
    '        "PAGADO": "Pagado",\n'
    '        "PAGO_ADELANTADO": "Pago adelantado",\n'
    '        "PAGADA": "Pagado",\n'
    "    }\n"
    "    return labels.get(c, codigo.strip() if codigo else \"-\")\n\n\n"
    "# SQL PostgreSQL"
)
if "def etiqueta_estado_cuota" not in t:
    if anchor not in t:
        raise SystemExit("cuota_estado anchor not found")
    t = t.replace(anchor, insert)
    ce.write_text(t, encoding="utf-8", newline="\n")
    print("patched cuota_estado.py")
else:
    print("skip cuota_estado.py (already)")

# --- recibo_pdf.py ---
rp = ROOT / "backend" / "app" / "services" / "cobros" / "recibo_pdf.py"
t = rp.read_text(encoding="utf-8")
if "estado_cuota" not in t.split("def generar_recibo_pago_reportado")[1].split(") -> bytes")[0]:
    t = t.replace(
        "    moneda: Optional[str] = None,\n    tasa_cambio: Optional[float] = None,\n) -> bytes:",
        "    moneda: Optional[str] = None,\n    tasa_cambio: Optional[float] = None,\n"
        "    estado_cuota: Optional[str] = None,\n) -> bytes:",
    )
else:
    print("recibo_pdf signature may already have estado_cuota")

# After cuotas_txt assignment, add estado display var
if "estado_cuota_display" not in t:
    t = t.replace(
        "    cuotas_txt = (aplicado_a_cuotas or \"\").strip() or \"Pendiente de aplicar\"\n\n    # Simbolo de moneda",
        "    cuotas_txt = (aplicado_a_cuotas or \"\").strip() or \"Pendiente de aplicar\"\n"
        '    estado_cuota_display = ((estado_cuota or "").strip() or None)\n\n    # Simbolo de moneda',
    )

# Append row to info before table = Table(info
old_info_close = """        ],\n    ]\n\n    table = Table(info, colWidths=[1.45 * inch, 2.0 * inch, 1.2 * inch, 1.45 * inch])"""
new_info_close = """        ],\n    ]\n    if estado_cuota_display:\n        info.append(\n            [\n                Paragraph("Estado (cuota)", label_style),\n                Paragraph(f"<b>{estado_cuota_display}</b>", value_style),\n                Paragraph("", label_style),\n                Paragraph("", value_style),\n            ]\n        )\n\n    table = Table(info, colWidths=[1.45 * inch, 2.0 * inch, 1.2 * inch, 1.45 * inch])"""
if "if estado_cuota_display:" not in t:
    if old_info_close not in t:
        raise SystemExit("recibo_pdf info block not found")
    t = t.replace(old_info_close, new_info_close)

# TableStyle - add background for last row if dynamic - use conditional via replace of fixed BACKGROUND (0, 4)
old_ts = """        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#f8fafc")),\n    ]))"""
new_ts = """        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#f8fafc")),\n    ]))\n    ts = list(table._cmds) if False else None  # placeholder"""
# Simpler: extend TableStyle list in source - read actual file after first replace

rp.write_text(t, encoding="utf-8", newline="\n")
print("recibo_pdf pass1 written")
