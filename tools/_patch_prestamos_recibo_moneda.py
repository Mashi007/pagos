# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
t = p.read_text(encoding="utf-8")

old_imp = """from app.services.cobros.recibo_cuota_amortizacion import generar_recibo_cuota_amortizacion

from app.services.cuota_estado import ("""
new_imp = """from app.services.cobros.recibo_cuota_amortizacion import generar_recibo_cuota_amortizacion
from app.services.cobros.recibo_cuota_moneda import contexto_moneda_montos_recibo_cuota

from app.services.cuota_estado import ("""
if old_imp not in t:
    raise SystemExit("import not found")
t = t.replace(old_imp, new_imp, 1)

old_fn = """    referencia = f"Cuota-{cuota.numero_cuota}-Prestamo-{prestamo_id}"

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

        fp_c = cuota.fecha_pago

        if isinstance(fp_c, datetime):

            fecha_recep = fp_c

            fecha_pago_date = fp_c.date()

        else:

            fecha_pago_date = fp_c

            fecha_recep = datetime.combine(fp_c, datetime.min.time())

    fv_c = cuota.fecha_vencimiento

    fv_date_c = fv_c.date() if fv_c and hasattr(fv_c, "date") else fv_c

    estado_codigo = estado_cuota_para_mostrar(total_pagado, monto_cuota, fv_date_c, hoy_negocio())

    estado_cuota_lbl = etiqueta_estado_cuota(estado_codigo)

    saldo_ini_s = f"{float(cuota.saldo_capital_inicial or 0):.2f}" if cuota.saldo_capital_inicial is not None else "-"

    saldo_fin_s = f"{float(cuota.saldo_capital_final or 0):.2f}" if cuota.saldo_capital_final is not None else "-"

    fpd = "-"

    if fecha_pago_date:

        fpd = fecha_pago_date.strftime("%d/%m/%Y")

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

        aplicado_a_cuotas=f"Cuota {cuota.numero_cuota}",

        saldo_inicial=saldo_ini_s,

        saldo_final=saldo_fin_s,

        numero_cuota=cuota.numero_cuota,

        fecha_pago_display=fpd,

        estado_cuota=estado_cuota_lbl,

    )"""
new_fn = """    referencia = f"Cuota-{cuota.numero_cuota}-Prestamo-{prestamo_id}"

    institucion = "N/A"

    numero_operacion = referencia

    fecha_recep = None

    fecha_pago_date = None

    pago = None

    if cuota.pago_id:

        pago = db.get(Pago, cuota.pago_id)

        if pago:

            institucion = (pago.institucion_bancaria or "N/A")[:100]

            numero_operacion = (pago.numero_documento or pago.referencia_pago or referencia)[:100]

            if pago.fecha_pago:

                fecha_recep = pago.fecha_pago

                fecha_pago_date = pago.fecha_pago.date() if hasattr(pago.fecha_pago, "date") else pago.fecha_pago

    if not fecha_recep and cuota.fecha_pago:

        fp_c = cuota.fecha_pago

        if isinstance(fp_c, datetime):

            fecha_recep = fp_c

            fecha_pago_date = fp_c.date()

        else:

            fecha_pago_date = fp_c

            fecha_recep = datetime.combine(fp_c, datetime.min.time())

    fv_c = cuota.fecha_vencimiento

    fv_date_c = fv_c.date() if fv_c and hasattr(fv_c, "date") else fv_c

    estado_codigo = estado_cuota_para_mostrar(total_pagado, monto_cuota, fv_date_c, hoy_negocio())

    estado_cuota_lbl = etiqueta_estado_cuota(estado_codigo)

    fpd = "-"

    if fecha_pago_date:

        fpd = fecha_pago_date.strftime("%d/%m/%Y")

    ctx = contexto_moneda_montos_recibo_cuota(db, prestamo, cuota, pago)

    pdf_bytes = generar_recibo_cuota_amortizacion(

        referencia_interna=referencia,

        nombres_completos=(prestamo.nombres or "").strip(),

        cedula=(prestamo.cedula or "").strip(),

        institucion_financiera=institucion,

        monto=ctx.monto_str,

        numero_operacion=numero_operacion,

        fecha_recepcion=fecha_recep,

        fecha_pago=fecha_pago_date,

        moneda=ctx.moneda,

        tasa_cambio=ctx.tasa_cambio,

        aplicado_a_cuotas=f"Cuota {cuota.numero_cuota}",

        saldo_inicial=ctx.saldo_inicial,

        saldo_final=ctx.saldo_final,

        numero_cuota=cuota.numero_cuota,

        fecha_pago_display=fpd,

        estado_cuota=estado_cuota_lbl,

    )"""
if old_fn not in t:
    raise SystemExit("function block not found")
t = t.replace(old_fn, new_fn, 1)

p.write_text(t, encoding="utf-8")
print("prestamos ok")
