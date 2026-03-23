from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
t = p.read_text(encoding="utf-8")
old = '''    if c not in ("todos", "fifo", "cascada", "sin_cupo"):

        raise HTTPException(status_code=400, detail="cohorte debe ser todos, fifo, cascada (alias de fifo) o sin_cupo")'''
new = '''    if c not in ("todos", "fifo", "sin_cupo"):

        raise HTTPException(status_code=400, detail="cohorte debe ser todos, fifo (alias: cascada), o sin_cupo")'''
if old not in t:
    raise SystemExit("pattern not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8", newline="\n")
print("ok")
