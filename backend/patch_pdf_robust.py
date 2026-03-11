# -*- coding: utf-8 -*-
"""Hacer robusta la generacion del PDF: try/except y valores por defecto."""
path = "app/api/v1/endpoints/estado_cuenta_publico.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1) En verificar_codigo: envolver obtencion de datos + generacion PDF en try/except
old_verify = """    rec = fila[0] if hasattr(fila, "__getitem__") else fila
    datos = _obtener_datos_pdf(db, cedula_lookup)
    if not datos:
        return VerificarCodigoResponse(ok=False, error="Error al generar el documento.")
    pdf_bytes = _generar_pdf_estado_cuenta(
        cedula=datos["cedula_display"],
        nombre=datos["nombre"],
        prestamos=datos["prestamos_list"],
        cuotas_pendientes=datos["cuotas_pendientes"],
        total_pendiente=datos["total_pendiente"],
        fecha_corte=datos["fecha_corte"],
        amortizaciones_por_prestamo=datos["amortizaciones_por_prestamo"],
    )
    import base64
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    rec.usado = True
    db.commit()
    return VerificarCodigoResponse(ok=True, pdf_base64=pdf_b64)"""

new_verify = """    rec = fila[0] if hasattr(fila, "__getitem__") else fila
    try:
        datos = _obtener_datos_pdf(db, cedula_lookup)
        if not datos:
            return VerificarCodigoResponse(ok=False, error="Error al generar el documento.")
        pdf_bytes = _generar_pdf_estado_cuenta(
            cedula=datos.get("cedula_display") or "",
            nombre=datos.get("nombre") or "",
            prestamos=datos.get("prestamos_list") or [],
            cuotas_pendientes=datos.get("cuotas_pendientes") or [],
            total_pendiente=float(datos.get("total_pendiente") or 0),
            fecha_corte=datos.get("fecha_corte") or date.today(),
            amortizaciones_por_prestamo=datos.get("amortizaciones_por_prestamo") or [],
        )
        import base64
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    except Exception as e:
        logger.exception("Error generando PDF estado de cuenta: %s", e)
        return VerificarCodigoResponse(
            ok=False,
            error="No se pudo generar el PDF. Intente de nuevo o solicite un nuevo codigo.",
        )
    rec.usado = True
    db.commit()
    return VerificarCodigoResponse(ok=True, pdf_base64=pdf_b64)"""

if "Error generando PDF estado de cuenta" not in c:
    c = c.replace(old_verify, new_verify, 1)

# 2) En _generar_pdf_estado_cuenta: asegurar total_pendiente es numero y valores por defecto
# Buscar la linea que usa total_pendiente en Paragraph
c = c.replace(
    'story.append(Paragraph(f"Total pendiente: {total_pendiente:.2f}", styles["Normal"]))',
    'story.append(Paragraph(f"Total pendiente: {float(total_pendiente or 0):.2f}", styles["Normal"]))',
    1,
)

# 3) En _obtener_datos_pdf: envolver el return en try/except para no propagar AttributeError/TypeError
# Insertar try al inicio del cuerpo de _obtener_datos_pdf y except antes del return final
# Mejor: en verificar ya usamos .get() y float(); el try/except global atrapa fallos en _obtener_datos_pdf y _generar_pdf.
# Opcional: en _obtener_datos_pdf hacer total_pendiente = float(total_pendiente) con try/except
# Ya hecho en new_verify con float(datos.get("total_pendiente") or 0).

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: PDF generation robust")
