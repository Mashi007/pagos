# Patch index.html CSP to allow inline script and style
path = "index.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
old = """    <!-- Permitir PDF en iframe (data:application/pdf;base64,...) para estado de cuenta y recibos -->
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; frame-src 'self' data: blob:;" />"""
new = """    <!-- CSP: default-src 'self'; permitir inline script/style (index.html + React/Tailwind). frame-src para PDF en iframe. -->
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' 'unsafe-hashes'; frame-src 'self' data: blob:;" />"""
if old not in c:
    print("Old CSP block not found")
    exit(1)
c = c.replace(old, new, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("CSP updated in index.html")
