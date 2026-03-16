# Fix getReciboCuotaPdf URL in prestamoService.ts
path = "src/services/prestamoService.ts"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

wrong = r"      \/\/cuotas/\/recibo.pdf\,"
right = "      `${this.baseUrl}/${prestamoId}/cuotas/${cuotaId}/recibo.pdf`,"
if wrong in content:
    content = content.replace(wrong, right)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("URL fixed")
else:
    print("Wrong string not found, checking...")
    import re
    m = re.search(r".*recibo\.pdf.*", content)
    if m:
        print(repr(m.group(0)))
