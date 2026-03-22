# One-off patch: run from repo root: python _patch_diagnostico_auditoria.py
from pathlib import Path

ROOT = Path(__file__).resolve().parent
p = ROOT / "backend" / "app" / "services" / "diagnostico_critico_service.py"
text = p.read_text(encoding="utf-8")

old_import = """from sqlalchemy import and_, text
from sqlalchemy.orm import Session

logging.basicConfig"""
new_import = """from sqlalchemy import and_, text
from sqlalchemy.orm import Session

from app.models.auditoria_conciliacion_manual import AuditoriaConciliacionManual

logging.basicConfig"""
if old_import not in text:
    raise SystemExit("import anchor not found")
text = text.replace(old_import, new_import, 1)

# Match INSERT block regardless of comment bytes (UTF-8 vs mojibake)
import re

pattern = re.compile(
    r"\n\s*# Registrar en auditor[^\n]*\n"
    r"\s*db\.execute\(text\('''\n"
    r"\s*INSERT INTO auditoria_conciliacion_manual[^\n]*\n"
    r"[\s\S]*?"
    r"\s*\}\)\s*\n\s*\n\s*db\.commit\(\)",
    re.MULTILINE,
)
replacement = """
            # Registrar en auditoria (ORM: AuditoriaConciliacionManual)
            db.add(
                AuditoriaConciliacionManual(
                    pago_id=ultimo_pago[1],
                    cuota_id=cuota_id,
                    monto_asignado=exceso,
                    tipo_asignacion="MANUAL",
                    resultado="EXITOSA",
                    motivo=f"Correccion de sobre-aplicacion: reduccion de {exceso}",
                )
            )

            db.commit()"""
m = pattern.search(text)
if not m:
    raise SystemExit("audit INSERT block not found")
text = text[: m.start()] + replacement + text[m.end() :]

p.write_text(text, encoding="utf-8")
print("patched", p)
