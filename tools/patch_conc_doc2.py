from pathlib import Path

P = Path(__file__).resolve().parents[1] / "backend" / "app" / "services" / "conciliacion_automatica_service.py"
text = P.read_text(encoding="utf-8")
start = text.index("    DOCUMENTACION = {")
end = text.index("    }\n\n    @classmethod", start) + len("    }")
old = text[start:end]
new = """    DOCUMENTACION = {
        PAGADO: 'Cuota cubierta al 100% (vencimiento ya cumplido o hoy).',
        PENDIENTE: 'Sin cubrir al 100%; al corriente (vencimiento hoy o futuro).',
        VENCIDO: 'Sin cubrir al 100%; 1 a 91 dias despues del vencimiento.',
        MORA: 'Sin cubrir al 100%; 92 o mas dias despues del vencimiento.',
        PARCIAL: 'Abonos sin cubrir al 100%; aun al corriente respecto al vencimiento.',
        PAGO_ADELANTADO: 'Cubierta al 100% antes de la fecha de vencimiento.',
        CANCELADA: 'Cuota anulada o no vigente. No requiere pago.',
    }"""
text = text[:start] + new + text[end:]
P.write_text(text, encoding="utf-8")
print("ok")
