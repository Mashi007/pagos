from pathlib import Path

P = Path(__file__).resolve().parents[1] / "frontend" / "src" / "services" / "pagoService.ts"
text = P.read_text(encoding="utf-8")

old_pago = """  usuario_registro: string

  notas: string | null

  documento_nombre: string | null"""
new_pago = """  usuario_registro: string

  notas: string | null

  moneda_registro?: string | null

  monto_bs_original?: number | null

  tasa_cambio_bs_usd?: number | null

  fecha_tasa_referencia?: string | null

  documento_nombre: string | null"""

if old_pago not in text:
    raise SystemExit("Pago interface anchor not found")
text = text.replace(old_pago, new_pago, 1)

old_create = """  notas?: string | null

  conciliado?: boolean
}"""
new_create = """  notas?: string | null

  conciliado?: boolean

  moneda_registro?: 'USD' | 'BS'

  tasa_cambio_manual?: number | null
}"""

if old_create not in text:
    raise SystemExit("PagoCreate anchor not found")
text = text.replace(old_create, new_create, 1)

old_g = """  async guardarFilaEditable(data: {
    cedula: string

    prestamo_id: number | null

    monto_pagado: number

    fecha_pago: string // formato "DD-MM-YYYY"

    numero_documento: string | null
  }):"""
new_g = """  async guardarFilaEditable(data: {
    cedula: string

    prestamo_id: number | null

    monto_pagado: number

    fecha_pago: string // formato "DD-MM-YYYY"

    numero_documento: string | null

    moneda_registro?: 'USD' | 'BS'

    tasa_cambio_manual?: number | null
  }):"""

if old_g not in text:
    raise SystemExit("guardarFilaEditable anchor not found")
text = text.replace(old_g, new_g, 1)

P.write_text(text, encoding="utf-8")
print("pagoService.ts patched")
