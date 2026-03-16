"""Fix SUBSTRING position: RPC-YYYYMMDD-XXXXX => digits start at 14, not 10."""
import pathlib

path = pathlib.Path(__file__).resolve().parent / "app" / "api" / "v1" / "endpoints" / "cobros_publico.py"
text = path.read_text(encoding="utf-8")
old = "SUBSTRING(referencia_interna FROM 10 FOR 5)"
new = "SUBSTRING(referencia_interna FROM 14 FOR 5)"
if old not in text:
    raise SystemExit("Pattern not found")
path.write_text(text.replace(old, new), encoding="utf-8")
print("Patched: FROM 10 FOR 5 -> FROM 14 FOR 5")
