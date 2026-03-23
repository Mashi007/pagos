"""Patch backend/app/api/v1/endpoints/pagos.py for BS/USD resolver."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
text = P.read_text(encoding="utf-8")

IMPORT_LINE = "from app.services.cobros.cedula_reportar_bs_service import (\n"
INSERT_IMPORT = (
    "from app.services.pago_registro_moneda import (\n"
    "    resolver_monto_registro_pago,\n"
    "    preload_autorizados_bs,\n"
    ")\n\n"
)

if "from app.services.pago_registro_moneda import" not in text:
    if IMPORT_LINE not in text:
        raise SystemExit("import anchor not found")
    text = text.replace(IMPORT_LINE, INSERT_IMPORT + IMPORT_LINE, 1)

OLD_CREAR = """    try:

        row = Pago(

            cedula_cliente=cedula_normalizada,

            prestamo_id=payload.prestamo_id,

            fecha_pago=fecha_pago_ts,

            monto_pagado=Decimal(str(round(monto_val, 2))),

            numero_documento=num_doc,

            institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,

            estado="PENDIENTE",

            notas=payload.notas.strip() if payload.notas else None,

            referencia_pago=ref,

            conciliado=conciliado,  # [B2] Usar solo conciliado, no verificado_concordancia

            fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,

            verificado_concordancia="SI" if conciliado else "",  # Legacy: sync con conciliado

            usuario_registro=usuario_registro,  # [MEJORADO] Usuario real desde JWT

        )"""

NEW_CREAR = """    try:

        monto_usd, moneda_fin, monto_bs_o, tasa_o, fecha_tasa_o = resolver_monto_registro_pago(

            db,

            cedula_normalizada=cedula_normalizada,

            fecha_pago=payload.fecha_pago,

            monto_pagado=Decimal(str(round(monto_val, 2))),

            moneda_registro=payload.moneda_registro or "USD",

            tasa_cambio_manual=payload.tasa_cambio_manual,

        )

        row = Pago(

            cedula_cliente=cedula_normalizada,

            prestamo_id=payload.prestamo_id,

            fecha_pago=fecha_pago_ts,

            monto_pagado=monto_usd,

            numero_documento=num_doc,

            institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,

            estado="PENDIENTE",

            notas=payload.notas.strip() if payload.notas else None,

            referencia_pago=ref,

            conciliado=conciliado,  # [B2] Usar solo conciliado, no verificado_concordancia

            fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,

            verificado_concordancia="SI" if conciliado else "",  # Legacy: sync con conciliado

            usuario_registro=usuario_registro,  # [MEJORADO] Usuario real desde JWT

            moneda_registro=moneda_fin,

            monto_bs_original=monto_bs_o,

            tasa_cambio_bs_usd=tasa_o,

            fecha_tasa_referencia=fecha_tasa_o,

        )"""

if OLD_CREAR not in text:
    raise SystemExit("crear_pago block not found")
text = text.replace(OLD_CREAR, NEW_CREAR, 1)

OLD_BATCH_LOOP = """        try:

            for idx, payload in enumerate(pagos_list):

                num_doc = docs_en_payload[idx] if idx < len(docs_en_payload) else normalize_documento(payload.numero_documento)

                if idx in errors_by_index:"""

NEW_BATCH_LOOP = """        try:

            autorizados_bs = preload_autorizados_bs(db)

            for idx, payload in enumerate(pagos_list):

                num_doc = docs_en_payload[idx] if idx < len(docs_en_payload) else normalize_documento(payload.numero_documento)

                if idx in errors_by_index:"""

if OLD_BATCH_LOOP not in text:
    raise SystemExit("batch loop anchor not found")
text = text.replace(OLD_BATCH_LOOP, NEW_BATCH_LOOP, 1)

OLD_BATCH_PAGO = """                cedula_normalizada = (payload.cedula_cliente or "").strip().upper()

                row = Pago(

                    cedula_cliente=cedula_normalizada,

                    prestamo_id=payload.prestamo_id,

                    fecha_pago=fecha_pago_ts,

                    monto_pagado=payload.monto_pagado,

                    numero_documento=num_doc,

                    institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,

                    estado="PENDIENTE",

                    notas=payload.notas.strip() if payload.notas else None,

                    referencia_pago=ref,

                    conciliado=conciliado,

                    fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,

                    verificado_concordancia="SI" if conciliado else "",

                    usuario_registro=usuario_registro,

                )"""

NEW_BATCH_PAGO = """                cedula_normalizada = (payload.cedula_cliente or "").strip().upper()

                es_valido_b, monto_val_b, err_msg_b = _validar_monto(payload.monto_pagado)

                if not es_valido_b:

                    raise HTTPException(status_code=400, detail=f"Lote fila {idx + 1}: {err_msg_b}")

                try:

                    monto_usd_b, moneda_fin_b, monto_bs_b, tasa_b, fecha_tasa_b = resolver_monto_registro_pago(

                        db,

                        cedula_normalizada=cedula_normalizada,

                        fecha_pago=payload.fecha_pago,

                        monto_pagado=Decimal(str(round(monto_val_b, 2))),

                        moneda_registro=payload.moneda_registro or "USD",

                        tasa_cambio_manual=payload.tasa_cambio_manual,

                        autorizados_bs=autorizados_bs,

                    )

                except HTTPException as e:

                    d = e.detail if isinstance(e.detail, str) else str(e.detail)

                    raise HTTPException(status_code=e.status_code, detail=f"Lote fila {idx + 1}: {d}") from e

                row = Pago(

                    cedula_cliente=cedula_normalizada,

                    prestamo_id=payload.prestamo_id,

                    fecha_pago=fecha_pago_ts,

                    monto_pagado=monto_usd_b,

                    numero_documento=num_doc,

                    institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,

                    estado="PENDIENTE",

                    notas=payload.notas.strip() if payload.notas else None,

                    referencia_pago=ref,

                    conciliado=conciliado,

                    fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,

                    verificado_concordancia="SI" if conciliado else "",

                    usuario_registro=usuario_registro,

                    moneda_registro=moneda_fin_b,

                    monto_bs_original=monto_bs_b,

                    tasa_cambio_bs_usd=tasa_b,

                    fecha_tasa_referencia=fecha_tasa_b,

                )"""

if OLD_BATCH_PAGO not in text:
    raise SystemExit("batch Pago block not found")
text = text.replace(OLD_BATCH_PAGO, NEW_BATCH_PAGO, 1)

P.write_text(text, encoding="utf-8")
print("pagos.py patched")
