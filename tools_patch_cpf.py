from pathlib import Path
p = Path("frontend/src/components/prestamos/CrearPrestamoForm.tsx")
t = p.read_text(encoding="utf-8")
# add SelectItem for DESISTIMIENTO if missing
if 'value="DESISTIMIENTO"' not in t:
    t = t.replace(
        '<SelectItem value="RECHAZADO">Rechazado</SelectItem>',
        '<SelectItem value="DESISTIMIENTO">Desistimiento</SelectItem>\n\n                        <SelectItem value="RECHAZADO">Rechazado</SelectItem>',
        1,
    )
p.write_text(t, encoding="utf-8", newline="\n")
print("CrearPrestamoForm select ok")
