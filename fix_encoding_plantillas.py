# Fix corrupted/literal Unicode and mojibake in Plantillas.tsx
import re

path = "frontend/src/pages/Plantillas.tsx"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Replace Unicode escapes with actual UTF-8 characters
c = c.replace("configuraci\\u00f3n", "configuración")
c = c.replace("Configuraci\\u00f3n", "Configuración")
c = c.replace("env\\u00edan", "envían")
c = c.replace("notificaci\\u00f3n", "notificación")
c = c.replace("c\\u00e9dula", "cédula")
c = c.replace("aqu\\u00ed", "aquí")

# Replace mojibake: sequence between </strong> and next word (e.g. "Asunto")
# Matches the corrupted en-dash that displays as â€" or ?"
c = re.sub(r"(</strong>)\s*[^\w\s\-]+\s*", r"\1 - ", c)

with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(c)
print("Fixed Plantillas.tsx")
