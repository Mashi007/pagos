from pathlib import Path

repls = [
    (
        Path(r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/services/cuota_estado.py"),
        '"VENCIDO": "Vencido (1-91 d)"',
        '"VENCIDO": "Vencido"',
    ),
    (
        Path(r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/utils/cuotaEstadoDisplay.ts"),
        "VENCIDO: 'Vencido (1-91 d)'",
        "VENCIDO: 'Vencido'",
    ),
    (
        Path(
            r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/components/prestamos/TablaAmortizacionPrestamo.tsx"
        ),
        "VENCIDO: 'Vencido (1-91 d)'",
        "VENCIDO: 'Vencido'",
    ),
]

for path, old, new in repls:
    t = path.read_text(encoding="utf-8")
    if old not in t:
        raise SystemExit(f"missing in {path}")
    path.write_text(t.replace(old, new, 1), encoding="utf-8", newline="\n")
    print("ok", path.name)

test_path = Path(r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/tests/test_cuota_estado.py")
tt = test_path.read_text(encoding="utf-8")
tt = tt.replace(
    'assert etiqueta_estado_cuota("VENCIDO") == "Vencido (1-91 d)"',
    'assert etiqueta_estado_cuota("VENCIDO") == "Vencido"',
)
if "Vencido (1-91 d)" in tt:
    tt = tt.replace("Vencido (1-91 d)", "Vencido")
test_path.write_text(tt, encoding="utf-8", newline="\n")
print("ok test_cuota_estado.py")
