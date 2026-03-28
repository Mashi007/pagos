from pathlib import Path

p = Path(__file__).resolve().parent / "app" / "services" / "cobros" / "recibo_pago_cartera_pdf.py"
t = p.read_text(encoding="utf-8")
old1 = "import io\nfrom typing import List, Optional"
new1 = "import io\nfrom pathlib import Path\nfrom typing import List, Optional"
old2 = '_LOGO_PATH = __import__("pathlib").Path(__file__).resolve().parent.parent.parent.parent / "static" / "logo.png"'
new2 = '_LOGO_PATH = Path(__file__).resolve().parent.parent.parent.parent / "static" / "logo.png"'
if old1 not in t or old2 not in t:
    raise SystemExit("pattern not found")
p.write_text(t.replace(old1, new1, 1).replace(old2, new2, 1), encoding="utf-8")
print("ok")
