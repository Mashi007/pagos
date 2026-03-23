# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "estado_cuenta_publico.py"
t = p.read_text(encoding="utf-8")

old = """from app.services.cobros.recibo_cuota_amortizacion import generar_recibo_cuota_amortizacion

from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos"""
new = """from app.services.cobros.recibo_cuota_amortizacion import generar_recibo_cuota_amortizacion
from app.services.cobros.recibo_cuota_moneda import contexto_moneda_montos_recibo_cuota

from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos"""
if old not in t:
    raise SystemExit("import block not found")
t = t.replace(old, new, 1)

old2 = """    referencia = f"Cuota-{cuota.numero_cuota}-Prestamo-{prestamo_id}"

    monto_str = f"{total_pagado:.2f}" if total_pagado > 0 else f"{monto_cuota:.2f}"

    institucion = "N/A"

    numero_operacion = referencia

    fecha_recep = None

    fecha_pago_date = None

    if cuota.pago_id:

        pago = db.get(Pago, cuota.pago_id)

        if pago:"""
new2 = """    referencia = f"Cuota-{cuota.numero_cuota}-Prestamo-{prestamo_id}"

    institucion = "N/A"

    numero_operacion = referencia

    fecha_recep = None

    fecha_pago_date = None

    pago = None

    if cuota.pago_id:

        pago = db.get(Pago, cuota.pago_id)

        if pago:"""
if old2 not in t:
    raise SystemExit("pago block not found")
t = t.replace(old2, new2, 1)

old3 = """    saldo_inicial_display = f"{float(cuota.saldo_capital_inicial or 0):,.2f} Bs." if cuota.saldo_capital_inicial else "-"

    saldo_final_display = f"{float(cuota.saldo_capital_final or 0):,.2f} Bs." if cuota.saldo_capital_final else "-"

    fecha_pago_display = fecha_pago_date.strftime("%d/%m/%Y") if fecha_pago_date else "-"

    tasa_hoy = None

    try:

        from app.services.tasa_cambio_service import obtener_tasa_hoy

        tasa_obj = obtener_tasa_hoy(db)

        tasa_hoy = float(tasa_obj.tasa_oficial) if tasa_obj else None

    except Exception:

        pass

    pdf_bytes = generar_recibo_cuota_amortizacion(

        referencia_interna=referencia,

        nombres_completos=(prestamo.nombres or "").strip(),

        cedula=(prestamo.cedula or "").strip(),

        institucion_financiera=institucion,

        monto=monto_str + " Bs.",

        numero_operacion=numero_operacion,

        fecha_recepcion=fecha_recep,

        fecha_pago=fecha_pago_date,

        aplicado_a_cuotas=f"Cuota {cuota.numero_cuota}",

        saldo_inicial=saldo_inicial_display,

        saldo_final=saldo_final_display,

        numero_cuota=cuota.numero_cuota,

        fecha_pago_display=fecha_pago_display,

        moneda="BS",

        tasa_cambio=tasa_hoy,

    )"""
new3 = """    fecha_pago_display = fecha_pago_date.strftime("%d/%m/%Y") if fecha_pago_date else "-"

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

        aplicado_a_cuotas=f"Cuota {cuota.numero_cuota}",

        saldo_inicial=ctx.saldo_inicial,

        saldo_final=ctx.saldo_final,

        numero_cuota=cuota.numero_cuota,

        fecha_pago_display=fecha_pago_display,

        moneda=ctx.moneda,

        tasa_cambio=ctx.tasa_cambio,

    )"""
if old3 not in t:
    raise SystemExit("saldo/pdf block not found")
t = t.replace(old3, new3, 1)

p.write_text(t, encoding="utf-8")
print("estado_cuenta ok")
