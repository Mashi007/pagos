from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
out = []
i = 0
while i < len(lines):
    line = lines[i]
    # Solo el Pago() de carga Excel (tiene comentario Autoconciliar encima)
    if (
        "cedula_cliente=cedula_fk" in line
        and i > 0
        and "Autoconciliar: pagos creados por carga Excel" in lines[i - 6]
    ):
        out.append(line.replace("cedula_cliente=cedula_fk", 'cedula_cliente=cedula.strip().upper() if cedula else ""'))
    else:
        out.append(line)
    i += 1

p.write_text("".join(out), encoding="utf-8", newline="\n")
print("OK")
