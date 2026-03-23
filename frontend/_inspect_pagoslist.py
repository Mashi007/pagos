from pathlib import Path

t = Path("src/components/pagos/PagosList.tsx").read_text(encoding="utf-8")
i = t.find("['cuotas-prestamo']")
print(repr(t[i - 120 : i + 220]))
