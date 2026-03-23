from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "schemas" / "pago.py"
lines = p.read_text(encoding="utf-8").splitlines()
ins = [
    "    # USD (defecto): monto_pagado en dolares. BS: monto_pagado en bolivares; requiere autorizacion lista Bs + tasa (BD o manual).",
    '    moneda_registro: Optional[str] = "USD"',
    "    tasa_cambio_manual: Optional[Decimal] = None  # Solo si no hay tasa en BD para fecha_pago",
]
idx = None
for i, l in enumerate(lines):
    if "conciliado: Optional[bool] = None" in l and "carga masiva" in l:
        idx = i + 1
        break
if idx is None:
    raise SystemExit("conciliado line not found")
lines[idx:idx] = ins
for i, l in enumerate(lines):
    if l.strip() == "class PagoUpdate(BaseModel):":
        val = [
            "",
            '    @field_validator("moneda_registro", mode="before")',
            "    @classmethod",
            "    def moneda_registro_opcional(cls, v: object) -> Optional[str]:",
            '        if v is None or v == "":',
            '            return "USD"',
            "        return str(v).strip().upper()",
            "",
        ]
        lines[i:i] = val
        break
for i, l in enumerate(lines):
    if l.strip() == "verificado_concordancia: Optional[str] = None  # SI / NO":
        lines.insert(i + 1, "    moneda_registro: Optional[str] = None")
        lines.insert(i + 2, "    tasa_cambio_manual: Optional[Decimal] = None")
        break
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("ok")
