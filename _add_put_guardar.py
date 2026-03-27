from pathlib import Path

p = Path("backend/app/api/v1/endpoints/pagos.py")
s = p.read_text(encoding="utf-8")
old = (
    '@router.post("/guardar-fila-editable", response_model=dict)\n\n'
    "def guardar_fila_editable("
)
new = (
    '@router.post("/guardar-fila-editable", response_model=dict)\n'
    '@router.put("/guardar-fila-editable", response_model=dict)\n\n'
    "def guardar_fila_editable("
)
if new not in s:
    assert old in s, "pattern missing"
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
print("done")
