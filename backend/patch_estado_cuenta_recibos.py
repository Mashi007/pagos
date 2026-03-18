# Script one-off: add recibos/token/base_url to estado_cuenta_publico and solicitar_estado_cuenta
import re

path = "app/api/v1/endpoints/estado_cuenta_publico.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) verificar_codigo: add recibos, token, base_url and pass to generar_pdf
old1 = """        if not datos:
            return VerificarCodigoResponse(ok=False, error="Error al generar el documento.")
        pdf_bytes = generar_pdf_estado_cuenta(
            cedula=datos.get("cedula_display") or "",
            nombre=datos.get("nombre") or "",
            prestamos=datos.get("prestamos_list") or [],
            cuotas_pendientes=datos.get("cuotas_pendientes") or [],
            total_pendiente=float(datos.get("total_pendiente") or 0),
            fecha_corte=datos.get("fecha_corte") or date.today(),
            amortizaciones_por_prestamo=datos.get("amortizaciones_por_prestamo") or [],
        )
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")"""

new1 = """        if not datos:
            return VerificarCodigoResponse(ok=False, error="Error al generar el documento.")
        recibos = _obtener_recibos_cliente(db, cedula_lookup)
        recibo_token = create_recibo_token(cedula_lookup, expire_hours=2)
        base_url = str(request.base_url).rstrip("/")
        pdf_bytes = generar_pdf_estado_cuenta(
            cedula=datos.get("cedula_display") or "",
            nombre=datos.get("nombre") or "",
            prestamos=datos.get("prestamos_list") or [],
            cuotas_pendientes=datos.get("cuotas_pendientes") or [],
            total_pendiente=float(datos.get("total_pendiente") or 0),
            fecha_corte=datos.get("fecha_corte") or date.today(),
            amortizaciones_por_prestamo=datos.get("amortizaciones_por_prestamo") or [],
            recibos=recibos,
            recibo_token=recibo_token,
            base_url=base_url,
        )
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")"""

if old1 in content:
    content = content.replace(old1, new1)
    print("Patched verificar_codigo call")
else:
    print("Old1 not found (maybe already patched)")

# 2) return VerificarCodigoResponse with recibo_token
content = content.replace(
    "return VerificarCodigoResponse(ok=True, pdf_base64=pdf_b64, expira_en=expira_en_iso)",
    "return VerificarCodigoResponse(ok=True, pdf_base64=pdf_b64, expira_en=expira_en_iso, recibo_token=recibo_token)",
)

# 3) solicitar_estado_cuenta: add recibos, base_url, recibo_token=None (informes)
old3 = """    pdf_bytes = generar_pdf_estado_cuenta(
        cedula=cedula_display,
        nombre=nombre,
        prestamos=prestamos_list,
        cuotas_pendientes=cuotas_pendientes,
        total_pendiente=total_pendiente,
        fecha_corte=fecha_corte,
        amortizaciones_por_prestamo=amortizaciones_por_prestamo,
    )

    if email:"""

new3 = """    recibos = _obtener_recibos_cliente(db, cedula_lookup)
    base_url = str(request.base_url).rstrip("/")
    usar_token = getattr(body, "origen", None) != "informes"
    recibo_token = create_recibo_token(cedula_lookup, expire_hours=2) if usar_token else None
    pdf_bytes = generar_pdf_estado_cuenta(
        cedula=cedula_display,
        nombre=nombre,
        prestamos=prestamos_list,
        cuotas_pendientes=cuotas_pendientes,
        total_pendiente=total_pendiente,
        fecha_corte=fecha_corte,
        amortizaciones_por_prestamo=amortizaciones_por_prestamo,
        recibos=recibos,
        recibo_token=recibo_token,
        base_url=base_url,
    )

    if email:"""

if old3 in content:
    content = content.replace(old3, new3)
    print("Patched solicitar_estado_cuenta call")
else:
    print("Old3 not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done.")
