from pathlib import Path

p = Path(r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/services/diagnostico_critico_service.py")
t = p.read_text(encoding="utf-8")
print("CURRENT_DATE count", t.count("CURRENT_DATE"))
print("c.monto count", t.count("c.monto"))
