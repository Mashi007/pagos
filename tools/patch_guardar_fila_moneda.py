from pathlib import Path

P = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
text = P.read_text(encoding="utf-8")

OLD_BODY = """class GuardarFilaEditableBody(BaseModel):

    \"\"\"Datos de una fila editable validada para guardar como Pago.\"\"\"

    cedula: str

    prestamo_id: Optional[int] = None

    monto_pagado: float

    fecha_pago: str  # formato "DD-MM-YYYY"

    numero_documento: Optional[str] = None"""

NEW_BODY = """class GuardarFilaEditableBody(BaseModel):

    \"\"\"Datos de una fila editable validada para guardar como Pago.\"\"\"

    cedula: str

    prestamo_id: Optional[int] = None

    monto_pagado: float

    fecha_pago: str  # formato "DD-MM-YYYY"

    numero_documento: Optional[str] = None

    moneda_registro: Optional[str] = "USD"

    tasa_cambio_manual: Optional[float] = None"""

if OLD_BODY not in text:
    raise SystemExit("GuardarFilaEditableBody not found")
text = text.replace(OLD_BODY, NEW_BODY, 1)

OLD_CREAR = """        # Crear pago

        # [A2] Marcar conciliado=True y verificado_concordancia="SI" desde el momento de la creaci�n,

        # ya que guardar-fila-editable implica que el pago fue revisado y validado manualmente.

        ref_pago = (numero_doc_norm or (numero_doc or "Carga"))[:_MAX_LEN_NUMERO_DOCUMENTO]

        ahora_conciliacion = datetime.now(ZoneInfo(TZ_NEGOCIO))

        pago = Pago(

            cedula_cliente=cedula_fk,

            prestamo_id=prestamo_id,

            fecha_pago=datetime.combine(fecha_pago, dt_time.min),

            monto_pagado=Decimal(str(round(monto, 2))),

            numero_documento=numero_doc_norm,

            estado="PENDIENTE",

            referencia_pago=ref_pago,

            conciliado=True,  # [B2] Usar solo conciliado

            fecha_conciliacion=ahora_conciliacion,

            verificado_concordancia="SI",  # Legacy: sync con conciliado

            usuario_registro=usuario_registro,

        )"""

# File may have encoding differences in comment - use shorter anchor
ANCHOR = """        ref_pago = (numero_doc_norm or (numero_doc or "Carga"))[:_MAX_LEN_NUMERO_DOCUMENTO]

        ahora_conciliacion = datetime.now(ZoneInfo(TZ_NEGOCIO))

        pago = Pago(

            cedula_cliente=cedula_fk,

            prestamo_id=prestamo_id,

            fecha_pago=datetime.combine(fecha_pago, dt_time.min),

            monto_pagado=Decimal(str(round(monto, 2))),

            numero_documento=numero_doc_norm,

            estado="PENDIENTE",

            referencia_pago=ref_pago,

            conciliado=True,  # [B2] Usar solo conciliado

            fecha_conciliacion=ahora_conciliacion,

            verificado_concordancia="SI",  # Legacy: sync con conciliado

            usuario_registro=usuario_registro,

        )"""

NEW_CREAR = """        ref_pago = (numero_doc_norm or (numero_doc or "Carga"))[:_MAX_LEN_NUMERO_DOCUMENTO]

        ahora_conciliacion = datetime.now(ZoneInfo(TZ_NEGOCIO))

        moneda_r = (body.moneda_registro or "USD").strip().upper()

        tasa_man_dec = None

        if body.tasa_cambio_manual is not None:

            tasa_man_dec = Decimal(str(body.tasa_cambio_manual))

        monto_usd_g, moneda_fin_g, monto_bs_g, tasa_g, fecha_tasa_g = resolver_monto_registro_pago(

            db,

            cedula_normalizada=(cedula_fk or "").strip().upper(),

            fecha_pago=fecha_pago,

            monto_pagado=Decimal(str(round(monto, 2))),

            moneda_registro=moneda_r,

            tasa_cambio_manual=tasa_man_dec,

        )

        pago = Pago(

            cedula_cliente=cedula_fk,

            prestamo_id=prestamo_id,

            fecha_pago=datetime.combine(fecha_pago, dt_time.min),

            monto_pagado=monto_usd_g,

            numero_documento=numero_doc_norm,

            estado="PENDIENTE",

            referencia_pago=ref_pago,

            conciliado=True,  # [B2] Usar solo conciliado

            fecha_conciliacion=ahora_conciliacion,

            verificado_concordancia="SI",  # Legacy: sync con conciliado

            usuario_registro=usuario_registro,

            moneda_registro=moneda_fin_g,

            monto_bs_original=monto_bs_g,

            tasa_cambio_bs_usd=tasa_g,

            fecha_tasa_referencia=fecha_tasa_g,

        )"""

if ANCHOR not in text:
    raise SystemExit("guardar fila Pago anchor not found")
text = text.replace(ANCHOR, NEW_CREAR, 1)

# Cuotas block uses monto > 0 - should use USD monto
text = text.replace(
    "        if pago.prestamo_id and monto > 0:",
    "        if pago.prestamo_id and float(pago.monto_pagado or 0) > 0:",
    1,
)

P.write_text(text, encoding="utf-8")
print("guardar fila patched")
