# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend/app/services/cobros/recibo_cuota_amortizacion.py"
t = p.read_text(encoding="utf-8")
old = """    fecha_pago_display: Optional[str] = None,
) -> bytes:"""
new = """    fecha_pago_display: Optional[str] = None,
    moneda: Optional[str] = None,
) -> bytes:"""
if old not in t:
    raise SystemExit("sig end not found")
t = t.replace(old, new, 1)
old2 = """        fecha_pago_display=fecha_pago_display,
    )"""
new2 = """        fecha_pago_display=fecha_pago_display,
        moneda=moneda,
    )"""
if old2 not in t:
    raise SystemExit("call end not found")
p.write_text(t.replace(old2, new2, 1), encoding="utf-8")
print("recibo_cuota_amortizacion moneda ok")
