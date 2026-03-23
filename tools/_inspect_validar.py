from pathlib import Path

s = Path(
    "c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/api/v1/endpoints/pagos.py"
).read_text(encoding="utf-8")
a = s.find("def validar_filas_batch")
b = s.find('@router.post("/guardar-fila-edit', a)
print("a", a, "b", b, "len", b - a)
print(s[b - 600 : b + 60])
