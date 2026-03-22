# python _patch_models_init.py
from pathlib import Path

p = Path(__file__).resolve().parent / "backend" / "app" / "models" / "__init__.py"
text = p.read_text(encoding="utf-8")

line_import = "from app.models.auditoria import Auditoria\n"
if "auditoria_conciliacion_manual" not in text:
    text = text.replace(
        line_import,
        line_import
        + "from app.models.auditoria_conciliacion_manual import AuditoriaConciliacionManual\n",
        1,
    )

if '"AuditoriaConciliacionManual"' not in text:
    text = text.replace(
        '    "Auditoria",\n',
        '    "Auditoria",\n    "AuditoriaConciliacionManual",\n',
        1,
    )

if '"PrestamoConError"' not in text.split("__all__", 1)[1]:
    text = text.replace(
        '    "ClienteConError",\n',
        '    "ClienteConError",\n    "PrestamoConError",\n',
        1,
    )

p.write_text(text, encoding="utf-8")
print("patched", p)
