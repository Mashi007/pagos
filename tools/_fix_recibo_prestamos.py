# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 1) recibo_cuota_amortizacion.py: pasar moneda
p1 = ROOT / "backend/app/services/cobros/recibo_cuota_amortizacion.py"
t1 = p1.read_text(encoding="utf-8")
old_sig = """def generar_recibo_cuota_amortizacion(
    referencia_interna: str,
    nombres_completos: str,
    cedula: str,
    institucion_financiera: str,
    monto: str,
    numero_operacion: str,
    fecha_recepcion: Optional[datetime] = None,
    fecha_pago: Optional[date] = None,
    aplicado_a_cuotas: Optional[str] = None,
    saldo_inicial: Optional[str] = None,
    saldo_final: Optional[str] = None,
    numero_cuota: Optional[int] = None,
    fecha_pago_display: Optional[str] = None,
) -> bytes:"""
new_sig = """def generar_recibo_cuota_amortizacion(
    referencia_interna: str,
    nombres_completos: str,
    cedula: str,
    institucion_financiera: str,
    monto: str,
    numero_operacion: str,
    fecha_recepcion: Optional[datetime] = None,
    fecha_pago: Optional[date] = None,
    aplicado_a_cuotas: Optional[str] = None,
    saldo_inicial: Optional[str] = None,
    saldo_final: Optional[str] = None,
    numero_cuota: Optional[int] = None,
    fecha_pago_display: Optional[str] = None,
    moneda: Optional[str] = None,
) -> bytes:"""
if old_sig not in t1:
    raise SystemExit("signature mismatch recibo_cuota_amortizacion")
t1 = t1.replace(old_sig, new_sig, 1)
old_ret = """    return generar_recibo_pago_reportado(
        referencia_interna=referencia_interna,
        nombres=(nombres_completos or "").strip(),
        apellidos="",
        tipo_cedula=tipo_cedula,
        numero_cedula=numero_cedula,
        institucion_financiera=institucion_financiera or "N/A",
        monto=monto,
        numero_operacion=numero_operacion or referencia_interna,
        fecha_recepcion=fecha_recepcion,
        fecha_pago=fecha_pago,
        aplicado_a_cuotas=aplicado_a_cuotas,
        saldo_inicial=saldo_inicial,
        saldo_final=saldo_final,
        numero_cuota=numero_cuota,
        fecha_pago_display=fecha_pago_display,
    )"""
new_ret = """    return generar_recibo_pago_reportado(
        referencia_interna=referencia_interna,
        nombres=(nombres_completos or "").strip(),
        apellidos="",
        tipo_cedula=tipo_cedula,
        numero_cedula=numero_cedula,
        institucion_financiera=institucion_financiera or "N/A",
        monto=monto,
        numero_operacion=numero_operacion or referencia_interna,
        fecha_recepcion=fecha_recepcion,
        fecha_pago=fecha_pago,
        aplicado_a_cuotas=aplicado_a_cuotas,
        saldo_inicial=saldo_inicial,
        saldo_final=saldo_final,
        numero_cuota=numero_cuota,
        fecha_pago_display=fecha_pago_display,
        moneda=moneda,
    )"""
if old_ret not in t1:
    raise SystemExit("return block mismatch recibo_cuota_amortizacion")
p1.write_text(t1.replace(old_ret, new_ret, 1), encoding="utf-8")
print("recibo_cuota_amortizacion ok")

# 2) prestamos.py: monto sin sufijo duplicado + moneda; fecha_pago seguro
p2 = ROOT / "backend/app/api/v1/endpoints/prestamos.py"
t2 = p2.read_text(encoding="utf-8")
old_block = """    monto_cuota = float(cuota.monto or 0)

    total_pagado = float(cuota.total_pagado or 0)

    if total_pagado <= 0 and monto_cuota <= 0:

        raise HTTPException(status_code=400, detail="La cuota no tiene monto pagado")

    referencia = f"Cuota-{cuota.numero_cuota}-Prestamo-{prestamo_id}"

    monto_str = f"{total_pagado:.2f}" if total_pagado > 0 else f"{monto_cuota:.2f}"

    institucion = "N/A"

    numero_operacion = referencia

    fecha_recep = None

    fecha_pago_date = None

    if cuota.pago_id:

        pago = db.get(Pago, cuota.pago_id)

        if pago:

            institucion = (pago.institucion_bancaria or "N/A")[:100]

            numero_operacion = (pago.numero_documento or pago.referencia_pago or referencia)[:100]

            if pago.fecha_pago:

                fecha_recep = pago.fecha_pago

                fecha_pago_date = pago.fecha_pago.date() if hasattr(pago.fecha_pago, "date") else pago.fecha_pago

    if not fecha_recep and cuota.fecha_pago:

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
new_block = """    monto_cuota = float(cuota.monto or 0)

    total_pagado = float(cuota.total_pagado or 0)

    if total_pagado <= 0 and monto_cuota <= 0:

        raise HTTPException(status_code=400, detail="La cuota no tiene monto pagado")

    referencia = f"Cuota-{cuota.numero_cuota}-Prestamo-{prestamo_id}"

    monto_str = f"{total_pagado:.2f}" if total_pagado > 0 else f"{monto_cuota:.2f}"

    institucion = "N/A"

    numero_operacion = referencia

    fecha_recep = None

    fecha_pago_date = None

    if cuota.pago_id:

        pago = db.get(Pago, cuota.pago_id)

        if pago:

            institucion = (pago.institucion_bancaria or "N/A")[:100]

            numero_operacion = (pago.numero_documento or pago.referencia_pago or referencia)[:100]

            if pago.fecha_pago:

                fecha_recep = pago.fecha_pago

                fp = pago.fecha_pago

                fecha_pago_date = fp.date() if hasattr(fp, "date") else fp

    if not fecha_recep and cuota.fecha_pago:

        fp_c = cuota.fecha_pago

        if hasattr(fp_c, "date") and not isinstance(fp_c, date):

            fecha_pago_date = fp_c.date()

            fecha_recep = fp_c if isinstance(fp_c, datetime) else datetime.combine(fp_c, datetime.min.time())

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
if old_block not in t2:
    raise SystemExit("prestamos recibo block mismatch")
# Ensure date is imported in prestamos - check for `from datetime import date, datetime`
if "from datetime import" not in t2.split("def get_recibo_cuota_pdf", 1)[0][-2000:]:
    pass
if "from datetime import date, datetime" not in t2 and "date" in new_block:
    # file likely has datetime imported; need date for isinstance
    if "from datetime import date" not in t2:
        # prepend after first datetime import line
        t2 = t2.replace(
            "from datetime import datetime",
            "from datetime import date, datetime",
            1,
        )
p2.write_text(t2.replace(old_block, new_block, 1), encoding="utf-8")
print("prestamos get_recibo ok")
