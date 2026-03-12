import os
path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
# Base64 puede estar en varias lineas; incluir \s en la clase
c = c.replace(
    "s = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+', '[Imagen]', html, flags=re.DOTALL)",
    "s = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=\\s]+', '[Imagen]', html, flags=re.DOTALL)"
)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK")
