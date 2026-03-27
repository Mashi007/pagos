from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\api\v1\endpoints\dashboard\kpis.py"
)
t = p.read_text(encoding="utf-8")
t = t.replace(
    "            func.count(Prestamo.id),\n        )",
    "            func.count(Prestamo.id).label(\"n_prestamos\"),\n        )",
    1,
)
t = t.replace(
    "    n_prestamos = int(row[3] or 0)",
    "    n_prestamos = int(row.n_prestamos or 0)",
    1,
)
p.write_text(t, encoding="utf-8")
print("ok")
