# Run from backend/: skip sending email when origen=informes in solicitar_estado_cuenta
path = "app/api/v1/endpoints/estado_cuenta_publico.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_block = """    if email:
        try:
            filename = f"estado_cuenta_{cedula_display.replace('-', '_')}.pdf"
            email_body = (f"Estimado(a) {nombre},\\n\\nSe adjunta su estado de cuenta con fecha de corte {fecha_corte.isoformat()}.\\n\\nSaludos,\\nRapiCredit")
            if get_email_activo_servicio("estado_cuenta"):"""

# Simpler: just add the condition
content = content.replace(
    "    if email:\n        try:",
    '    enviar_por_email = email and getattr(body, "origen", None) != "informes"\n    if enviar_por_email:\n        try:',
)
content = content.replace(
    'mensaje = "Estado de cuenta generado. Se ha enviado una copia al correo registrado." if email else "Estado de cuenta generado."',
    'mensaje = "Estado de cuenta generado. Se ha enviado una copia al correo registrado." if enviar_por_email else "Estado de cuenta generado."',
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done: informes no envia email.")
