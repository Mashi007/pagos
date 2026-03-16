# One-off patch: handle duplicate referencia_interna (retry once + friendly message)
import re

path = "app/api/v1/endpoints/cobros_publico.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Ensure IntegrityError is imported (already done manually)
if "from sqlalchemy.exc import IntegrityError" not in content:
    content = content.replace(
        "from sqlalchemy import select, func",
        "from sqlalchemy import select, func\nfrom sqlalchemy.exc import IntegrityError",
    )

# 2) Replace the try block with retry logic
old_block = r"""    try:
        referencia = _generar_referencia_interna\(db\)
        nombres = \(cliente\.nombres or ""\)\.strip\(\)
        apellidos = ""  # clientes tiene solo nombres; si hay apellido en otro campo se puede mapear
        if " " in nombres:
            parts = nombres\.split\(None, 1\)
            nombres = parts\[0\]
            apellidos = parts\[1\] if len\(parts\) > 1 else ""

        pr = PagoReportado\(
            referencia_interna=referencia,
            nombres=nombres,
            apellidos=apellidos,
            tipo_cedula=tipo_cedula\.strip\(\)\.upper\(\),
            numero_cedula=numero_cedula\.strip\(\),
            fecha_pago=fecha_pago,
            institucion_financiera=institucion_financiera\.strip\(\)\[:100\],
            numero_operacion=numero_operacion\.strip\(\)\[:100\],
            monto=monto,
            moneda=\(moneda or "BS"\)\.strip\(\)\[:10\],
            comprobante=content,
            comprobante_nombre=filename\[:255\],
            comprobante_tipo=ctype,
            ruta_comprobante=None,
            observacion=observacion\[:300\] if observacion else None,
            correo_enviado_a=cliente\.email,
            estado="pendiente",
        \)
        db\.add\(pr\)
        db\.commit\(\)
        db\.refresh\(pr\)"""

new_block = """    try:
        pr = None
        referencia = None
        for _attempt in range(2):
            try:
                referencia = _generar_referencia_interna(db)
                nombres = (cliente.nombres or "").strip()
                apellidos = ""  # clientes tiene solo nombres; si hay apellido en otro campo se puede mapear
                if " " in nombres:
                    parts = nombres.split(None, 1)
                    nombres = parts[0]
                    apellidos = parts[1] if len(parts) > 1 else ""

                pr = PagoReportado(
                    referencia_interna=referencia,
                    nombres=nombres,
                    apellidos=apellidos,
                    tipo_cedula=tipo_cedula.strip().upper(),
                    numero_cedula=numero_cedula.strip(),
                    fecha_pago=fecha_pago,
                    institucion_financiera=institucion_financiera.strip()[:100],
                    numero_operacion=numero_operacion.strip()[:100],
                    monto=monto,
                    moneda=(moneda or "BS").strip()[:10],
                    comprobante=content,
                    comprobante_nombre=filename[:255],
                    comprobante_tipo=ctype,
                    ruta_comprobante=None,
                    observacion=observacion[:300] if observacion else None,
                    correo_enviado_a=cliente.email,
                    estado="pendiente",
                )
                db.add(pr)
                db.commit()
                db.refresh(pr)
                break
            except IntegrityError as ie:
                db.rollback()
                err_msg = str(ie.orig) if getattr(ie, "orig", None) else str(ie)
                if _attempt == 0 and "referencia_interna" in err_msg:
                    logger.warning("[COBROS_PUBLIC] Duplicate referencia_interna, retrying once: %s", ie)
                    continue
                return EnviarReporteResponse(
                    ok=False,
                    error="Ya existe un reporte con esa referencia. Si enviaste el formulario dos veces, no hace falta volver a enviar. Si no, intenta de nuevo en un momento.",
                )"""

# Use simple string replace (exact)
old_plain = """    try:
        referencia = _generar_referencia_interna(db)
        nombres = (cliente.nombres or "").strip()
        apellidos = ""  # clientes tiene solo nombres; si hay apellido en otro campo se puede mapear
        if " " in nombres:
            parts = nombres.split(None, 1)
            nombres = parts[0]
            apellidos = parts[1] if len(parts) > 1 else ""

        pr = PagoReportado(
            referencia_interna=referencia,
            nombres=nombres,
            apellidos=apellidos,
            tipo_cedula=tipo_cedula.strip().upper(),
            numero_cedula=numero_cedula.strip(),
            fecha_pago=fecha_pago,
            institucion_financiera=institucion_financiera.strip()[:100],
            numero_operacion=numero_operacion.strip()[:100],
            monto=monto,
            moneda=(moneda or "BS").strip()[:10],
            comprobante=content,
            comprobante_nombre=filename[:255],
            comprobante_tipo=ctype,
            ruta_comprobante=None,
            observacion=observacion[:300] if observacion else None,
            correo_enviado_a=cliente.email,
            estado="pendiente",
        )
        db.add(pr)
        db.commit()
        db.refresh(pr)"""

if old_plain in content:
    content = content.replace(old_plain, new_block, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patch applied OK")
else:
    print("Block not found")
    # Show what we have around referencia
    i = content.find("referencia = _generar_referencia_interna")
    if i >= 0:
        print(content[i:i+500])
