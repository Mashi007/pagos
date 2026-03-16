# Ensure recibo is always sent to client email: add helper and use it everywhere
path = "app/api/v1/endpoints/cobros.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add helper before _registrar_historial
old_historial = "def _registrar_historial(db: Session, pago_id: int, estado_anterior: str, estado_nuevo: str, usuario_email: Optional[str], motivo: Optional[str]):"
helper = '''def _email_cliente_pago_reportado(db: Session, pr: PagoReportado) -> str:
    """Email del cliente para enviar recibo: pr.correo_enviado_a o, si falta, busqueda por cedula en clientes."""
    to = (pr.correo_enviado_a or "").strip()
    if to and "@" in to:
        return to
    cedula_norm = (f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}").replace("-", "").strip()
    if not cedula_norm:
        return ""
    cliente = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_norm)
    ).scalars().first()
    if cliente and (cliente.email or "").strip():
        return (cliente.email or "").strip()
    return ""


def _registrar_historial(db: Session, pago_id: int, estado_anterior: str, estado_nuevo: str, usuario_email: Optional[str], motivo: Optional[str]):'''

if old_historial in content and "def _email_cliente_pago_reportado" not in content:
    content = content.replace(old_historial, helper)
    print("Added _email_cliente_pago_reportado")
else:
    print("Skip helper:", "already present" if "def _email_cliente_pago_reportado" in content else "block not found")

# 2) enviar_recibo_manual: use helper and keep respetar_destinos
old_enviar = """    to_email = (pr.correo_enviado_a or "").strip()
    if not to_email:
        raise HTTPException(status_code=400, detail="No hay correo registrado para este pago.")"""
new_enviar = """    to_email = _email_cliente_pago_reportado(db, pr)
    if not to_email:
        raise HTTPException(status_code=400, detail="No hay correo del cliente para este pago. Registre el correo en el detalle del pago o en la ficha del cliente.")"""
if old_enviar in content:
    content = content.replace(old_enviar, new_enviar)
    print("Updated enviar_recibo_manual to use _email_cliente_pago_reportado")
else:
    print("enviar_recibo block:", "not found" if "to_email = (pr.correo_enviado_a" not in content else "already updated or different")

# 3) aprobar: use helper for to_email
old_aprobar = "    to_email = (pr.correo_enviado_a or "").strip()\n    mensaje_final = \"Pago aprobado y recibo enviado por correo.\"\n    if to_email:"
new_aprobar = "    to_email = _email_cliente_pago_reportado(db, pr)\n    if not pr.correo_enviado_a and to_email:\n        pr.correo_enviado_a = to_email\n    mensaje_final = \"Pago aprobado y recibo enviado por correo.\"\n    if to_email:"
# Be careful - there might be two similar blocks (aprobar and PATCH). Let me do only the first occurrence for aprobar.
idx = content.find("    to_email = (pr.correo_enviado_a or \"\").strip()\n    mensaje_final = \"Pago aprobado y recibo enviado por correo.\"")
if idx >= 0:
    content = content[:idx] + "    to_email = _email_cliente_pago_reportado(db, pr)\n    if not pr.correo_enviado_a and to_email:\n        pr.correo_enviado_a = to_email\n    mensaje_final = \"Pago aprobado y recibo enviado por correo.\"" + content[idx + len("    to_email = (pr.correo_enviado_a or \"\").strip()\n    mensaje_final = \"Pago aprobado y recibo enviado por correo.\""):]
    print("Updated aprobar to use _email_cliente_pago_reportado")
else:
    print("aprobar to_email block not found")

# 4) rechazar: use helper
old_rechazar = "    to_email = (pr.correo_enviado_a or \"\").strip()\n    if to_email:\n        body_text = ("
new_rechazar = "    to_email = _email_cliente_pago_reportado(db, pr)\n    if to_email:\n        body_text = ("
if old_rechazar in content:
    content = content.replace(old_rechazar, new_rechazar)
    print("Updated rechazar to use _email_cliente_pago_reportado")
else:
    print("rechazar block not found")

# 5) PATCH estado aprobado: use helper
old_patch = "        to_email = (pr.correo_enviado_a or \"\").strip()\n        if to_email:\n            body_mail = "
new_patch = "        to_email = _email_cliente_pago_reportado(db, pr)\n        if not pr.correo_enviado_a and to_email:\n            pr.correo_enviado_a = to_email\n        if to_email:\n            body_mail = "
if old_patch in content:
    content = content.replace(old_patch, new_patch)
    print("Updated PATCH estado to use _email_cliente_pago_reportado")
else:
    print("PATCH to_email block not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done.")
