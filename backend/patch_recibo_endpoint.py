# -*- coding: utf-8 -*-
"""Add GET prestamos/{id}/cuotas/{cuota_id}/recibo.pdf endpoint."""
path = "app/api/v1/endpoints/prestamos.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

endpoint_code = '''
@router.get("/{prestamo_id}/cuotas/{cuota_id}/recibo.pdf")
def get_recibo_cuota_pdf(prestamo_id: int, cuota_id: int, db: Session = Depends(get_db)):
    """Genera el recibo PDF de una cuota (mismo formato que cobros)."""
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Prestamo no encontrado")
    cuota = db.get(Cuota, cuota_id)
    if not cuota or cuota.prestamo_id != prestamo_id:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")
    monto_cuota = float(cuota.monto or 0)
    total_pagado = float(cuota.total_pagado or 0)
    if total_pagado <= 0 and monto_cuota <= 0:
        raise HTTPException(status_code=400, detail="La cuota no tiene monto pagado")
    referencia = f"Cuota-{cuota.numero_cuota}-Prestamo-{prestamo_id}"
    monto_str = f"{total_pagado:.2f}" if total_pagado > 0 else f"{monto_cuota:.2f}"
    institucion = "N/A"
    numero_operacion = referencia
    fecha_recep = None
    if cuota.pago_id:
        pago = db.get(Pago, cuota.pago_id)
        if pago:
            institucion = (pago.institucion_bancaria or "N/A")[:100]
            numero_operacion = (pago.numero_documento or pago.referencia_pago or referencia)[:100]
            if pago.fecha_pago:
                fecha_recep = pago.fecha_pago
    if not fecha_recep and cuota.fecha_pago:
        from datetime import datetime as dt
        fecha_recep = dt.combine(cuota.fecha_pago, dt.min.time())
    pdf_bytes = generar_recibo_cuota_amortizacion(
        referencia_interna=referencia,
        nombres_completos=(prestamo.nombres or "").strip(),
        cedula=(prestamo.cedula or "").strip(),
        institucion_financiera=institucion,
        monto=monto_str + " Bs.",
        numero_operacion=numero_operacion,
        fecha_recepcion=fecha_recep,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_cuota_{cuota.numero_cuota}_{prestamo.cedula}.pdf"'},
    )
'''

marker = "def _obtener_cuotas_para_export"
idx = content.find(marker)
if idx == -1:
    raise SystemExit("Marker _obtener_cuotas_para_export not found")
# Insert after "return resultado" of get_cuotas_prestamo (last occurrence before marker)
chunk = content[:idx]
last_return = chunk.rfind("return resultado")
if last_return == -1:
    raise SystemExit("return resultado not found")
# Find end of that line and next newlines
end = chunk.find("\n", last_return)
while end != -1 and end < len(chunk):
    n = chunk.find("\n", end + 1)
    if n == -1:
        end = len(chunk)
        break
    # Stop at next def or non-empty non-space line
    rest = chunk[end + 1:n].strip()
    if rest.startswith("def ") or (rest and not rest.startswith("#")):
        break
    end = n
insert_at = end + 1
content = content[:insert_at] + endpoint_code + "\n" + content[insert_at:]
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Endpoint added OK")
