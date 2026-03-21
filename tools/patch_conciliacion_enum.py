from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "backend" / "app" / "services" / "conciliacion_automatica_service.py"
text = P.read_text(encoding="utf-8")

if "hoy_negocio" not in text:
    text = text.replace(
        "from app.models.cuota import Cuota\n",
        "from app.models.cuota import Cuota\n"
        "from app.services.cuota_estado import clasificar_estado_cuota, hoy_negocio\n",
        1,
    )

old = """    @staticmethod
    def calcular_estado_actualizado(db: Session, cuota_id: int) -> str:
        cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            return EstadoCuota.PENDIENTE
        
        monto_aplicado = ValidadorSobreAplicacion.obtener_monto_aplicado_actual(db, cuota_id)
        monto_total = Decimal(str(cuota.monto or 0))
        
        if monto_aplicado >= monto_total - Decimal('0.01'):
            return EstadoCuota.PAGADO
        elif monto_aplicado > 0:
            return EstadoCuota.PARCIAL
        else:
            if cuota.dias_mora and cuota.dias_mora > 0:
                  return EstadoCuota.MORA if cuota.dias_mora > 90 else EstadoCuota.VENCIDO
            else:
                  return EstadoCuota.PENDIENTE"""

new = """    @staticmethod
    def calcular_estado_actualizado(db: Session, cuota_id: int) -> str:
        cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            return EstadoCuota.PENDIENTE

        monto_aplicado = ValidadorSobreAplicacion.obtener_monto_aplicado_actual(db, cuota_id)
        monto_total_f = float(cuota.monto or 0)
        total_pagado_f = float(monto_aplicado)
        fv = cuota.fecha_vencimiento
        fv_d = fv.date() if fv and hasattr(fv, "date") else fv
        return clasificar_estado_cuota(total_pagado_f, monto_total_f, fv_d, hoy_negocio())"""

if old not in text:
    raise SystemExit("calcular_estado block not found")
text = text.replace(old, new, 1)

text = text.replace(
    "    PAGADO = 'PAGADO'\n    PENDIENTE = 'PENDIENTE'\n    MORA = 'MORA'\n    PARCIAL = 'PARCIAL'",
    "    PAGADO = 'PAGADO'\n    PENDIENTE = 'PENDIENTE'\n    VENCIDO = 'VENCIDO'\n    MORA = 'MORA'\n"
    "    PARCIAL = 'PARCIAL'\n    PAGO_ADELANTADO = 'PAGO_ADELANTADO'",
    1,
)

text = text.replace(
    "    ESTADOS_VALIDOS = {PAGADO, PENDIENTE, MORA, PARCIAL, CANCELADA}",
    "    ESTADOS_VALIDOS = {PAGADO, PENDIENTE, VENCIDO, MORA, PARCIAL, PAGO_ADELANTADO, CANCELADA}",
    1,
)

text = text.replace(
    "        PENDIENTE: 'Cuota sin pagar o con vencimiento futuro. No hay aplicaciones o aplicación parcial.',\n        MORA:",
    "        PENDIENTE: 'Cuota sin pagar o con vencimiento futuro. Sin abonos o a tiempo.',\n"
    "        VENCIDO: 'Cuota no cubierta y 1 a 91 dias despues del vencimiento.',\n"
    "        PAGO_ADELANTADO: 'Cuota cubierta antes de la fecha de vencimiento.',\n        MORA:",
    1,
)

P.write_text(text, encoding="utf-8")
print("conciliacion_automatica_service patched")
