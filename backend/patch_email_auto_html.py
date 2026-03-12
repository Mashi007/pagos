# Cuando body_html es None pero body_text es HTML, usar body_text como HTML
# y generar plain desde el strip. Asi Gmail recibe multipart/alternative y muestra HTML.
import os
path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Buscar el bloque justo antes de "# Asegurar body_html es str"
old = """        else:
            try:
                body_text.encode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                body_text = body_text.encode("utf-8", errors="replace").decode("utf-8")
        # Asegurar body_html es str y UTF-8 valido (evita HTML corrupto por encoding BD/plantilla)
        if body_html is not None:"""

new = """        else:
            try:
                body_text.encode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                body_text = body_text.encode("utf-8", errors="replace").decode("utf-8")
        # Si el caller envio HTML solo en body_text (sin body_html), tratar como HTML para que Gmail renderice
        if body_html is None and body_text and "<" in body_text and ">" in body_text:
            if "<table" in body_text.lower() or "</table>" in body_text or "<html" in body_text.lower() or "<body" in body_text.lower():
                body_html = body_text
        # Asegurar body_html es str y UTF-8 valido (evita HTML corrupto por encoding BD/plantilla)
        if body_html is not None:"""

if "Si el caller envio HTML solo en body_text" in c:
    print("Already patched")
else:
    c = c.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Patched: auto-detect HTML in body_text when body_html is None")
print("Done")
