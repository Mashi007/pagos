# -*- coding: utf-8 -*-
"""Define moneda_symbol en recibo_pdf.py (evita NameError -> HTTP 500)."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend/app/services/cobros/recibo_pdf.py"
t = p.read_text(encoding="utf-8")
needle = "    cuotas_txt = (aplicado_a_cuotas or \"\").strip() or \"Pendiente de aplicar\"\n\n    buf = io.BytesIO()"
insert = """    cuotas_txt = (aplicado_a_cuotas or \"\").strip() or \"Pendiente de aplicar\"

    # Simbolo de moneda en tablas (antes faltaba y causaba NameError al generar PDF)
    _m = (moneda or \"\").strip()
    if _m:
        moneda_symbol = _m
    else:
        md_u = (monto_display or \"\").upper()
        if \"USD\" in md_u:
            moneda_symbol = \"\"
        elif \"BS\" in md_u:
            moneda_symbol = \"\"
        else:
            moneda_symbol = \"Bs.\"

    buf = io.BytesIO()"""
if needle not in t:
    raise SystemExit("needle not found in recibo_pdf.py")
if "moneda_symbol =" in t and "Simbolo de moneda" in t:
    print("already patched")
else:
    p.write_text(t.replace(needle, insert, 1), encoding="utf-8")
    print("recibo_pdf.py ok")
