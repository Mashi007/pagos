p = r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/services/cuota_estado.py"
t = open(p, encoding="utf-8").read()
old = '    """Texto para UI/PDF (misma nomenclatura que la tabla de amortizacion en frontend)."""'
new = '    """Texto para UI/PDF (misma nomenclatura que la tabla de amortización en frontend)."""'
if old in t:
    t = t.replace(old, new)
    open(p, "w", encoding="utf-8", newline="\n").write(t)
print("ok")
