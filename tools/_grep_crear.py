from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend/src/components/prestamos/CrearPrestamoForm.tsx"
lines = p.read_text(encoding="utf-8").splitlines()
for i, line in enumerate(lines, 1):
    if any(
        k in line.lower()
        for k in ("cuota", "anticipo", "valoractivo", "valor activo", "total_financiamiento")
    ):
        print(f"{i}|{line}")
