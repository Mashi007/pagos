# Fix: cuando body_text es el mismo HTML que body_html, la parte text/plain muestra
# el codigo fuente (incl. base64) y el cliente lo muestra como "mensaje corrupto".
# Solucion: generar una version solo texto para text/plain cuando el cuerpo sea HTML.
import re
import os
path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")

def strip_html_to_plain(html: str, max_len: int = 8000) -> str:
    """Quita tags HTML y reemplaza data URLs por texto corto para parte text/plain."""
    if not html or not html.strip():
        return ""
    s = html
    # Quitar data:image/...;base64,... (puede ser muy largo)
    s = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+', '[Imagen]', s, flags=re.DOTALL)
    # Quitar comentarios HTML
    s = re.sub(r'<!--.*?-->', '', s, flags=re.DOTALL)
    # Quitar tags
    s = re.sub(r'<[^>]+>', ' ', s)
    # Colapsar espacios y saltos
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) > max_len:
        s = s[:max_len] + "..."
    return s if s else "Contenido en HTML. Abra en un cliente de correo compatible."

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Tras normalizar body_html, si body_text parece HTML (contiene < y >) y tenemos body_html,
# usar version solo texto para body_text
old_block = """            if "base64/" in body_html:
                body_html = body_html.replace("base64/", "base64,")

        if has_attachments:"""

new_block = """            if "base64/" in body_html:
                body_html = body_html.replace("base64/", "base64,")

        # Si body_text es el mismo HTML que body_html, el cliente puede mostrar text/plain
        # y se ve el codigo fuente + base64 como "mensaje corrupto". Usar version solo texto.
        if body_html and body_text and ("<" in body_text and ">" in body_text):
            body_text = strip_html_to_plain(body_text)

        if has_attachments:"""

if "strip_html_to_plain" in c:
    print("Already patched")
else:
    # Add the function after the encoders import (inside try, we need it before use)
    # Actually we need the function at module level so it can be called in try block.
    # Add after AttachmentType = ...
    c = c.replace(
        "# Tipo para adjuntos: (nombre_archivo, contenido_bytes)\nAttachmentType = Tuple[str, bytes]",
        """# Tipo para adjuntos: (nombre_archivo, contenido_bytes)
AttachmentType = Tuple[str, bytes]


def _strip_html_to_plain(html: str, max_len: int = 8000) -> str:
    '''Quita tags y data URLs para usar como parte text/plain cuando el cuerpo es HTML.'''
    if not html or not html.strip():
        return ""
    import re
    s = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+', '[Imagen]', html, flags=re.DOTALL)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.DOTALL)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\\\\s+', ' ', s).strip()
    return (s[:max_len] + "...") if len(s) > max_len else (s or "Contenido en HTML. Abra en un cliente compatible.")"""
    )
    # Fix the regex - we need \\s+ for whitespace
    c = c.replace("s = re.sub(r'\\\\s+', ' ', s).strip()", "s = re.sub(r'\\s+', ' ', s).strip()")
    c = c.replace("strip_html_to_plain(body_text)", "_strip_html_to_plain(body_text)")
    c = c.replace(new_block.strip(), new_block.strip())
    if "Si body_text es el mismo HTML" not in c:
        c = c.replace(
            """            if "base64/" in body_html:
                body_html = body_html.replace("base64/", "base64,")

        if has_attachments:""",
            """            if "base64/" in body_html:
                body_html = body_html.replace("base64/", "base64,")

        # Si body_text es el mismo HTML que body_html, el cliente puede mostrar text/plain
        # y se ve el codigo fuente + base64 como mensaje corrupto. Usar version solo texto.
        if body_html and body_text and ("<" in body_text and ">" in body_text):
            body_text = _strip_html_to_plain(body_text)

        if has_attachments:"""
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Patched: plain part now uses stripped text when body is HTML")
