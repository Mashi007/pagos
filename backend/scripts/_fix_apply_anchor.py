p = r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/scripts/apply_recibo_estado_cuota.py"
t = open(p, encoding="utf-8").read()
t = t.replace(
    '"    )\\n\\n\\n# SQL PostgreSQL"',
    '"    )\\n\\n# SQL PostgreSQL"',
    1,
)
open(p, "w", encoding="utf-8", newline="\n").write(t)
print("ok")
