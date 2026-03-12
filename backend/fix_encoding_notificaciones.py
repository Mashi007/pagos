# Fix UTF-8 encoding: file has Latin-1 bytes (0xf1 = n tilde) that break on Linux/Render
import os

path = os.path.join(os.path.dirname(__file__), "app", "api", "v1", "endpoints", "notificaciones.py")
with open(path, "r", encoding="cp1252") as f:
    content = f.read()
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("notificaciones.py: re-saved as UTF-8")

# Also fix notificaciones_tabs.py if it has the same issue
path_tabs = os.path.join(os.path.dirname(__file__), "app", "api", "v1", "endpoints", "notificaciones_tabs.py")
try:
    with open(path_tabs, "r", encoding="utf-8") as f:
        f.read()
    print("notificaciones_tabs.py: already UTF-8")
except UnicodeDecodeError:
    with open(path_tabs, "r", encoding="cp1252") as f:
        content = f.read()
    with open(path_tabs, "w", encoding="utf-8") as f:
        f.write(content)
    print("notificaciones_tabs.py: re-saved as UTF-8")
