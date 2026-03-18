# Add GET /recibo endpoint to cobros_publico for descarga con token (estado de cuenta)
path = "app/api/v1/endpoints/cobros_publico.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add imports
old_imports = "from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request"
new_imports = "from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query\nfrom fastapi.responses import Response"
content = content.replace(old_imports, new_imports)

old_email = "from app.core.email import send_email"
new_email = "from app.core.email import send_email\nfrom app.core.security import decode_token"
content = content.replace(old_email, new_email)

# Append endpoint before the last blank lines
endpoint = '''

@router.get("/recibo")
def get_recibo_publico(
    token: str = Query(..., description="Token de sesion estado de cuenta"),
    pago_id: int = Query(..., description="ID del pago reportado"),
    db: Session = Depends(get_db),
):
    """
    Devuelve el PDF del recibo del pago reportado. Requiere token valido (emitido al verificar codigo en estado de cuenta).
    Publico, sin auth; la seguridad es el token (cedula + expiracion).
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "recibo":
        raise HTTPException(status_code=401, detail="Token invalido o expirado.")
    cedula_token = (payload.get("sub") or "").strip()
    if not cedula_token:
        raise HTTPException(status_code=401, detail="Token invalido.")
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Recibo no encontrado.")
    pr = pr[0] if hasattr(pr, "__getitem__") else pr
    cedula_pr = (getattr(pr, "tipo_cedula", "") or "") + (getattr(pr, "numero_cedula", "") or "")
    if cedula_pr.replace("-", "") != cedula_token.replace("-", ""):
        raise HTTPException(status_code=403, detail="No tiene permiso para este recibo.")
    pdf_bytes = getattr(pr, "recibo_pdf", None)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="No hay recibo PDF para este pago.")
    ref = getattr(pr, "referencia_interna", "recibo") or "recibo"
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_{ref}.pdf"'},
    )
'''

# Insert before the very end (after the last except block and the closing of the file)
marker = "        return EnviarReporteResponse(\n            ok=False,\n            error=\"No se pudo procesar el reporte. Intente de nuevo o contacte por WhatsApp 424-4579934.\",\n        )"
if marker in content:
    content = content.replace(marker, marker + endpoint)
else:
    content = content.rstrip() + endpoint + "\n"

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("cobros_publico.py patched: GET /recibo added.")
