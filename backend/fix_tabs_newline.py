# Fix literal backtick-r-backtick-n in notificaciones_tabs.py
path = "app/api/v1/endpoints/notificaciones_tabs.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
# Replace the broken pattern with proper two lines
content = content.replace(
    '"]`r`n                        pdf_bytes = generar_carta_cobranza_pdf(ctx_pdf, db=db)',
    '"]\n                        pdf_bytes = generar_carta_cobranza_pdf(ctx_pdf, db=db)',
)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed")
