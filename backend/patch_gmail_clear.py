# Asegurar que Gmail reciba el correo claro y sin mensaje corrupto:
# 1) Nunca dejar text/plain vacio cuando hay HTML (fallback para Gmail)
# 2) Fijar Content-Type charset en partes plain/html por compatibilidad Gmail
import os
path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1) Tras _strip_html_to_plain, si body_text quedo vacio usar fallback
old = """        # Si body_text es el mismo HTML que body_html, el cliente puede mostrar text/plain
        # y se ve el codigo fuente + base64 como mensaje corrupto. Usar version solo texto.
        if body_html and body_text and ("<" in body_text and ">" in body_text):
            body_text = _strip_html_to_plain(body_text)

        if has_attachments:"""
new = """        # Gmail: si body_text es HTML, usar version solo texto para text/plain (evita ver codigo+base64)
        if body_html and body_text and ("<" in body_text and ">" in body_text):
            body_text = _strip_html_to_plain(body_text)
        if body_html and (not body_text or not body_text.strip()):
            body_text = "Contenido en HTML. Si no ve el formato correcto, abra el correo en Gmail o otro cliente compatible."

        if has_attachments:"""
if "Si no ve el formato correcto" in c:
    print("Fallback already present")
else:
    c = c.replace(old, new)
    print("Added plain fallback for Gmail")

# 2) Usar MIMEText con charset explicito y Content-Disposition inline para parte HTML (algunos clientes)
# En Python MIMEText(_, "html", "utf-8") ya pone charset. Opcional: forzar header.
# Reemplazar alt.attach(MIMEText(body_html, "html", "utf-8")) por version que setea charset
# Ya lo hace MIMEText. No cambiamos.

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Done")
