from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "schemas" / "pago.py"
text = p.read_text(encoding="utf-8")
old = """    notas: Optional[str] = None
    conciliado: Optional[bool] = None  # SA-/No en carga masiva

    @field_validator("numero_documento", mode="before")"""
new = """    notas: Optional[str] = None
    conciliado: Optional[bool] = None  # SA-/No en carga masiva
    # USD (defecto): monto_pagado en dolares. BS: monto_pagado en bolivares; requiere autorizacion lista Bs + tasa (BD o manual).
    moneda_registro: Optional[str] = "USD"
    tasa_cambio_manual: Optional[Decimal] = None  # Solo si no hay tasa en BD para fecha_pago

    @field_validator("numero_documento", mode="before")"""
if old not in text:
    raise SystemExit("anchor1 not found")
text = text.replace(old, new, 1)
old2 = """        return v


class PagoUpdate(BaseModel):"""
new2 = """        return v

    @field_validator("moneda_registro", mode="before")
    @classmethod
    def moneda_registro_opcional(cls, v: object) -> Optional[str]:
        if v is None or v == "":
            return "USD"
        return str(v).strip().upper()


class PagoUpdate(BaseModel):"""
if old2 not in text:
    raise SystemExit("anchor2 not found")
text = text.replace(old2, new2, 1)
old3 = """    verificado_concordancia: Optional[str] = None  # SI / NO

    @field_validator("numero_documento", mode="before")
    @classmethod
    def numero_documento_cualquier_formato_update"""
new3 = """    verificado_concordancia: Optional[str] = None  # SI / NO
    moneda_registro: Optional[str] = None
    tasa_cambio_manual: Optional[Decimal] = None

    @field_validator("numero_documento", mode="before")
    @classmethod
    def numero_documento_cualquier_formato_update"""
if old3 not in text:
    raise SystemExit("anchor3 not found")
text = text.replace(old3, new3, 1)
p.write_text(text, encoding="utf-8")
print("ok")
