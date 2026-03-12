# Si cuerpo es HTML pero body_html quedo None, setear body_html = cuerpo
# para que email.py reciba la parte HTML y Gmail renderice.
path = "app/api/v1/endpoints/notificaciones_tabs.py"
import os
path = os.path.join(os.path.dirname(__file__), path)
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old = """        if plantilla_id and db:
            plantilla = db.get(PlantillaNotificacion, plantilla_id)
            if plantilla and getattr(plantilla, "tipo", None) == "COBRANZA" and item.get("contexto_cobranza"):
                body_html = cuerpo  # el cuerpo de COBRANZA es HTML
                incluir_pdf_anexo = tipo_cfg.get("incluir_pdf_anexo") is not False"""

new = """        if plantilla_id and db:
            plantilla = db.get(PlantillaNotificacion, plantilla_id)
            if plantilla and getattr(plantilla, "tipo", None) == "COBRANZA" and item.get("contexto_cobranza"):
                body_html = cuerpo  # el cuerpo de COBRANZA es HTML
                incluir_pdf_anexo = tipo_cfg.get("incluir_pdf_anexo") is not False
        if body_html is None and cuerpo and ("</table>" in cuerpo or "<table" in cuerpo.lower()):
            body_html = cuerpo  # cualquier cuerpo HTML: enviar como body_html para que Gmail renderice"""

if "cualquier cuerpo HTML" in c:
    print("Already patched")
else:
    c = c.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Patched: body_html = cuerpo when body looks like HTML")
print("Done")
