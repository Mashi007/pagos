from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "services" / "estado_cuenta_pdf.py"
text = p.read_text(encoding="utf-8")
old = """                puede_recibo = (
                    estado_codigo in ("PAGADO", "PAGO_ADELANTADO")
                    and cuota_id
                    and base_url
                    and recibo_token
                )"""
new = """                # PAGADA: mismo código que en cuota_estado / UI (etiqueta "Pagado").
                puede_recibo = (
                    estado_codigo in ("PAGADO", "PAGADA", "PAGO_ADELANTADO")
                    and cuota_id
                    and base_url
                    and recibo_token
                )"""
if old not in text:
    raise SystemExit("pattern not found")
p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched", p)
