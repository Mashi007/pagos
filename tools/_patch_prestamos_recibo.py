# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend/app/api/v1/endpoints/prestamos.py"
t = p.read_text(encoding="utf-8")
old = """    if not fecha_recep and cuota.fecha_pago:

        fecha_recep = datetime.combine(cuota.fecha_pago, datetime.min.time())

        fecha_pago_date = cuota.fecha_pago

    pdf_bytes = generar_recibo_cuota_amortizacion(

        referencia_interna=referencia,

        nombres_completos=(prestamo.nombres or "").strip(),

        cedula=(prestamo.cedula or "").strip(),

        institucion_financiera=institucion,

        monto=monto_str + " Bs.",

        numero_operacion=numero_operacion,

        fecha_recepcion=fecha_recep,

        fecha_pago=fecha_pago_date,

    )"""
new = """    if not fecha_recep and cuota.fecha_pago:

        fp_c = cuota.fecha_pago

        if isinstance(fp_c, datetime):

            fecha_recep = fp_c

            fecha_pago_date = fp_c.date()

        else:

            fecha_pago_date = fp_c

            fecha_recep = datetime.combine(fp_c, datetime.min.time())

    pdf_bytes = generar_recibo_cuota_amortizacion(

        referencia_interna=referencia,

        nombres_completos=(prestamo.nombres or "").strip(),

        cedula=(prestamo.cedula or "").strip(),

        institucion_financiera=institucion,

        monto=monto_str,

        numero_operacion=numero_operacion,

        fecha_recepcion=fecha_recep,

        fecha_pago=fecha_pago_date,

        moneda="Bs.",

    )"""
if old not in t:
    raise SystemExit("prestamos block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("prestamos recibo ok")
