"""Patch: replace pass with db.rollback() in pg_advisory_xact_lock except block."""
import pathlib

path = pathlib.Path(__file__).resolve().parent / "app" / "api" / "v1" / "endpoints" / "cobros_publico.py"
text = path.read_text(encoding="utf-8")
old = '                except Exception:\n                    pass  # BD no PostgreSQL o lock no disponible'
new = '                except Exception:\n                    db.rollback()  # Dejar transacción limpia; continuar sin lock'
if old not in text:
    raise SystemExit("Block not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Patched.")
