from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "backend" / "app" / "services" / "conciliacion_automatica_service.py"
text = P.read_text(encoding="utf-8")
old = """    DOCUMENTACION = {
        PAGADO: 'Cuota completamente pagada. Monto aplicado >= monto de la cuota.',
        PENDIENTE: 'Cuota sin pagar o con vencimiento futuro. No hay aplicaciones o aplicaciAA3n parcial.',
        MORA: 'Cuota vencida (fecha_vencimiento < hoy) y sin pagar completamente. Estado de riesgo de cobranza.',
        PARCIAL: 'Cuota con pagos parciales aplicados. Monto aplicado < monto de la cuota.',
        CANCELADA: 'Cuota anulada o no vigente. No requiere pago.',
    }"""
new = """    DOCUMENTACION = {
        PAGADO: 'Cuota cubierta al 100% (vencimiento ya cumplido o hoy).',
        PENDIENTE: 'Sin cubrir al 100%; al corriente (vencimiento hoy o futuro).',
        VENCIDO: 'Sin cubrir al 100%; 1 a 91 dias despues del vencimiento.',
        MORA: 'Sin cubrir al 100%; 92 o mas dias despues del vencimiento.',
        PARCIAL: 'Abonos sin cubrir al 100%; aun al corriente respecto al vencimiento.',
        PAGO_ADELANTADO: 'Cubierta al 100% antes de la fecha de vencimiento.',
        CANCELADA: 'Cuota anulada o no vigente. No requiere pago.',
    }"""
if old not in text:
    raise SystemExit("DOCUMENTACION block not found (encoding?)")
text = text.replace(old, new, 1)
P.write_text(text, encoding="utf-8")
print("doc ok")
