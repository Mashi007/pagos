# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "app" / "services" / "cobros" / "recibo_pdf.py"
t = p.read_text(encoding="utf-8")

old_row = """        [
            Paragraph("TITULAR", label_style),
            Paragraph(nombre_completo or "-", value_style),
            Paragraph("C\u00c9DULA", label_style),
            Paragraph(cedula or "-", value_style),
        ],"""

new_row = """        [
            Paragraph("TITULAR", label_style),
            Paragraph(nombre_completo or "-", value_style),
            Paragraph("", label_style),
            Paragraph("", label_style),
        ],"""

if old_row not in t:
    # archivo podria tener CEDULA sin tilde o otro encoding
    import re

    m = re.search(
        r'(\s+\[\s*\n\s*Paragraph\("TITULAR", label_style\),\s*\n\s*Paragraph\(nombre_completo or "-", value_style\),\s*\n\s*Paragraph\("C.{0,4}DULA", label_style\),\s*\n\s*Paragraph\(cedula or "-", value_style\),\s*\n\s*\],)',
        t,
    )
    if not m:
        raise SystemExit("titular/cedula row not found")
    t = t.replace(m.group(1), "\n" + new_row + "\n", 1)
else:
    t = t.replace(old_row, new_row, 1)

old_style = """        ("GRID", (0, 0), (-1, -1), 0.35, _c["border"]),
        ("SPAN", (1, 3), (3, 3)),
"""

new_style = """        ("GRID", (0, 0), (-1, -1), 0.35, _c["border"]),
        ("SPAN", (1, 1), (3, 1)),
        ("SPAN", (1, 3), (3, 3)),
"""

if old_style not in t:
    raise SystemExit("info_style block not found")
t = t.replace(old_style, new_style, 1)

p.write_text(t, encoding="utf-8")
print("ok", p)
