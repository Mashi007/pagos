# Reemplazar imagenes inline (data:image/...;base64,...) por URL del logo en body_html.
# Asi el HTML es pequeno y Gmail lo renderiza; la imagen se carga por URL.
import re
import os
path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Anadir funcion que devuelve la URL del logo (misma logica que plantilla_cobranza)
helper = '''
def _logo_url_for_email():
    """URL del logo para reemplazar base64 inline en HTML (evita mensaje enorme que Gmail no renderiza)."""
    try:
        from app.core.config import settings
        base = (getattr(settings, "FRONTEND_PUBLIC_URL", None) or "https://rapicredit.onrender.com/pagos").rstrip("/")
    except Exception:
        base = "https://rapicredit.onrender.com/pagos"
    return f"{base}/logos/rapicredit-public.png"


'''

# Insertar despues de _strip_html_to_plain
if "_logo_url_for_email" in c:
    print("Already present")
else:
    c = c.replace(
        'return (s[:max_len] + "...") if len(s) > max_len else (s or "Contenido en HTML. Abra en un cliente compatible.")\n\n\ndef _sanitize_imap_error',
        'return (s[:max_len] + "...") if len(s) > max_len else (s or "Contenido en HTML. Abra en un cliente compatible.")\n\n' + helper + 'def _sanitize_imap_error'
    )
    print("Added _logo_url_for_email")

# En el bloque donde normalizamos body_html, despues de base64/ -> base64,, reemplazar data:image...base64,... por URL
old = '''            if "base64/" in body_html:
                body_html = body_html.replace("base64/", "base64,")

        # Gmail: si body_text es HTML'''
new = '''            if "base64/" in body_html:
                body_html = body_html.replace("base64/", "base64,")
            # Reemplazar imagenes inline base64 por URL del logo: HTML pequeno = Gmail renderiza bien
            logo_url = _logo_url_for_email()
            body_html = re.sub(
                r\'src="data:image/[^"]+"\',
                f\'src="{logo_url}"\',
                body_html,
                count=0,
                flags=re.DOTALL,
            )

        # Gmail: si body_text es HTML'''
if "Reemplazar imagenes inline base64 por URL" in c:
    print("Replace block already present")
else:
    c = c.replace(old, new)
    # ensure re is imported at top (we use it in _strip_html_to_plain with import re inside; re is also used here)
    if "import re" not in c[:2500]:
        c = c.replace("import logging\nimport time", "import logging\nimport re\nimport time")
    print("Added inline base64 -> URL replacement")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Done")
