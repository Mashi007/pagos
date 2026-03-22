"""Patch pagos.py: import tasa service + BS conversion in importar_un_pago_reportado_a_pagos."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
text = path.read_text(encoding="utf-8")

needle = "from app.services.cuota_estado import clasificar_estado_cuota, dias_retraso_desde_vencimiento\n\n\n"
ins = (
    needle
    + "from app.services.tasa_cambio_service import (\n\n    convertir_bs_a_usd,\n\n    obtener_tasa_por_fecha,\n\n)\n\n\n"
)
if "convertir_bs_a_usd" not in text:
    if needle not in text:
        raise SystemExit("import anchor missing")
    text = text.replace(needle, ins, 1)

old = (
    "    prestamo_id = prestamos[0].id\n\n"
    "    monto = float(pr.monto or 0)\n\n"
    "    if monto < _MIN_MONTO_PAGADO:\n\n"
    "        return _err_con_pce(\n\n"
    "            f\"Monto debe ser mayor a {_MIN_MONTO_PAGADO}\",\n\n"
    "            cedula_cliente=cedula_raw,\n\n"
    "            prestamo_id=prestamo_id,\n\n"
    "        )\n\n\n\n"
    "    ref_pago = (numero_doc_norm or numero_doc_raw or \"Cobros\")[:_MAX_LEN_NUMERO_DOCUMENTO]\n\n"
    "    ahora_imp = datetime.now(ZoneInfo(TZ_NEGOCIO))\n\n"
    "    p = Pago(\n\n"
    "        cedula_cliente=cedula_raw,\n\n"
    "        prestamo_id=prestamo_id,\n\n"
    "        fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),\n\n"
    "        monto_pagado=Decimal(str(round(monto, 2))),\n\n"
    "        numero_documento=numero_doc_norm,\n\n"
    "        estado=\"PENDIENTE\",\n\n"
    "        referencia_pago=ref_pago,\n\n"
    "        usuario_registro=usuario_email,\n\n"
    "        conciliado=True,\n\n"
    "        fecha_conciliacion=ahora_imp,\n\n"
    "        verificado_concordancia=\"SI\",\n\n"
    "    )\n\n"
)

new = (
    "    prestamo_id = prestamos[0].id\n\n"
    "    moneda_pr = (getattr(pr, \"moneda\", None) or \"USD\").strip().upper()\n\n"
    "    if moneda_pr == \"USDT\":\n\n"
    "        moneda_pr = \"USD\"\n\n"
    "    monto = float(pr.monto or 0)\n\n"
    "    monto_bs_original = None\n\n"
    "    tasa_aplicada = None\n\n"
    "    fecha_tasa_ref = None\n\n"
    "    if moneda_pr == \"BS\":\n\n"
    "        if not pr.fecha_pago:\n\n"
    "            return _err_con_pce(\n\n"
    "                \"Fecha de pago requerida para convertir bolivares a USD\",\n\n"
    "                cedula_cliente=cedula_raw,\n\n"
    "                prestamo_id=prestamo_id,\n\n"
    "            )\n\n"
    "        tasa_obj = obtener_tasa_por_fecha(db, pr.fecha_pago)\n\n"
    "        if tasa_obj is None:\n\n"
    "            return _err_con_pce(\n\n"
    "                \"No hay tasa de cambio registrada para la fecha de pago \"\n\n"
    "                f\"{pr.fecha_pago.isoformat()}; no se puede importar en bolivares\",\n\n"
    "                cedula_cliente=cedula_raw,\n\n"
    "                prestamo_id=prestamo_id,\n\n"
    "            )\n\n"
    "        tasa_aplicada = float(tasa_obj.tasa_oficial)\n\n"
    "        monto_bs_original = monto\n\n"
    "        try:\n\n"
    "            monto = convertir_bs_a_usd(monto_bs_original, tasa_aplicada)\n\n"
    "        except ValueError as e:\n\n"
    "            return _err_con_pce(str(e), cedula_cliente=cedula_raw, prestamo_id=prestamo_id)\n\n"
    "        fecha_tasa_ref = pr.fecha_pago\n\n"
    "    elif moneda_pr != \"USD\":\n\n"
    "        return _err_con_pce(\n\n"
    "            f\"Moneda no soportada en importacion: {moneda_pr}\",\n\n"
    "            cedula_cliente=cedula_raw,\n\n"
    "            prestamo_id=prestamo_id,\n\n"
    "        )\n\n"
    "    if monto < _MIN_MONTO_PAGADO:\n\n"
    "        return _err_con_pce(\n\n"
    "            f\"Monto debe ser mayor a {_MIN_MONTO_PAGADO}\",\n\n"
    "            cedula_cliente=cedula_raw,\n\n"
    "            prestamo_id=prestamo_id,\n\n"
    "        )\n\n\n\n"
    "    ref_pago = (numero_doc_norm or numero_doc_raw or \"Cobros\")[:_MAX_LEN_NUMERO_DOCUMENTO]\n\n"
    "    ahora_imp = datetime.now(ZoneInfo(TZ_NEGOCIO))\n\n"
    "    p = Pago(\n\n"
    "        cedula_cliente=cedula_raw,\n\n"
    "        prestamo_id=prestamo_id,\n\n"
    "        fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),\n\n"
    "        monto_pagado=Decimal(str(round(monto, 2))),\n\n"
    "        numero_documento=numero_doc_norm,\n\n"
    "        estado=\"PENDIENTE\",\n\n"
    "        referencia_pago=ref_pago,\n\n"
    "        usuario_registro=usuario_email,\n\n"
    "        conciliado=True,\n\n"
    "        fecha_conciliacion=ahora_imp,\n\n"
    "        verificado_concordancia=\"SI\",\n\n"
    "        moneda_registro=moneda_pr,\n\n"
    "        monto_bs_original=Decimal(str(round(monto_bs_original, 2))) if monto_bs_original is not None else None,\n\n"
    "        tasa_cambio_bs_usd=Decimal(str(tasa_aplicada)) if tasa_aplicada is not None else None,\n\n"
    "        fecha_tasa_referencia=fecha_tasa_ref,\n\n"
    "    )\n\n"
)

if old not in text:
    raise SystemExit("old block not found")
text = text.replace(old, new, 1)

old_resp = (
    '        "documento_ruta": getattr(row, "documento_ruta", None),\n\n'
    '        "cuotas_atrasadas": cuotas_atrasadas,\n\n'
    "    }\n"
)
new_resp = (
    '        "documento_ruta": getattr(row, "documento_ruta", None),\n\n'
    '        "cuotas_atrasadas": cuotas_atrasadas,\n\n'
    '        "moneda_registro": getattr(row, "moneda_registro", None),\n\n'
    '        "monto_bs_original": float(row.monto_bs_original) if getattr(row, "monto_bs_original", None) is not None else None,\n\n'
    '        "tasa_cambio_bs_usd": float(row.tasa_cambio_bs_usd) if getattr(row, "tasa_cambio_bs_usd", None) is not None else None,\n\n'
    '        "fecha_tasa_referencia": row.fecha_tasa_referencia.isoformat() if getattr(row, "fecha_tasa_referencia", None) else None,\n\n'
    "    }\n"
)
if '"moneda_registro"' not in text:
    if old_resp not in text:
        raise SystemExit("_pago_to_response block not found")
    text = text.replace(old_resp, new_resp, 1)

path.write_text(text, encoding="utf-8")
print("OK pagos.py")
