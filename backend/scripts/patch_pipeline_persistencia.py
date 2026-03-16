# Patch: add "Regla de persistencia" to pipeline docstring
import re

path = "app/services/pagos_gmail/pipeline.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

if "Regla de persistencia" in content:
    print("Already patched")
    exit(0)

# Add after "Sin imagenes: 1 fila por correo ... NA)." and before closing """
pattern = r'(Sin im[aá]genes: 1 fila por correo \(datos de asunto/cuerpo o NA\)\.)\s*"""'
replacement = r'''\1

Regla de persistencia: cada ejecucion de descarga INSERTA en la BD a continuacion del ultimo dato ya procesado;
nunca se borran ni sobrescriben registros previos al iniciar una descarga (solo se agregan nuevos PagosGmailSyncItem).
"""'''

new_content = re.sub(pattern, replacement, content)
if new_content == content:
    # Try simpler pattern
    pattern2 = r'(1 fila por correo \(datos de asunto/cuerpo o NA\)\.)\s*\n"""'
    replacement2 = r'''\1

Regla de persistencia: cada ejecucion de descarga INSERTA en la BD a continuacion del ultimo dato ya procesado;
nunca se borran ni sobrescriben registros previos al iniciar una descarga (solo se agregan nuevos PagosGmailSyncItem).
"""'''
    new_content = re.sub(pattern2, replacement2, content)

if new_content != content:
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Patched OK")
else:
    print("Pattern not found")
