# Anadir fallback body_html = cuerpo cuando el cuerpo es HTML (para Gmail).
import os
path = os.path.join(os.path.dirname(__file__), "app", "api", "v1", "endpoints", "notificaciones_tabs.py")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
needle = 'logging.getLogger(__name__).exception("Error generando PDF cobranza: %s", e)'
after = "\n        # Email: en modo prueba"
new_block = '\n        if body_html is None and cuerpo and ("</table>" in cuerpo or "<table" in cuerpo.lower()):\n            body_html = cuerpo  # cualquier cuerpo HTML\n        # Email: en modo prueba'
if "cualquier cuerpo HTML" in c:
    print("Already patched")
else:
    c = c.replace(needle + "\n                )\n        # Email: en modo prueba", needle + "\n                )" + new_block)
    if "cualquier cuerpo HTML" not in c:
        c = c.replace("\n        # Email: en modo prueba todos van solo", new_block + " todos van solo")
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Patched" if "cualquier cuerpo HTML" in c else "Check replace")
print("Done")
