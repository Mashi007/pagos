from pathlib import Path
path = Path("backend/app/api/v1/endpoints/pagos.py")
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
# find block after valid_prestamo_ids assignment
for i, ln in enumerate(lines):
    if "valid_prestamo_ids = {r for r in ids_rows" in ln:
        insert_at = i + 1
        break
else:
    raise SystemExit("valid_prestamo_ids assign not found")
block = [
    "        prestamo_estado_por_id: dict[int, str] = {}\n",
    "\n",
    "        if prestamo_ids:\n",
    "\n",
    "            er_rows = db.execute(select(Prestamo.id, Prestamo.estado).where(Prestamo.id.in_(prestamo_ids))).all()\n",
    "\n",
    "            prestamo_estado_por_id = {int(r[0]): (r[1] or \"\") for r in er_rows if r[0] is not None}\n",
    "\n",
]
lines[insert_at:insert_at] = block
path.write_text("".join(lines), encoding="utf-8", newline="\n")
print("preload ok", insert_at)
