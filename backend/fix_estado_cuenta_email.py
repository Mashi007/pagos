# Fix email_body syntax in estado_cuenta_publico.py
path = "app/api/v1/endpoints/estado_cuenta_publico.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_line = 'email_body = (\\r\\n                f"Estimado(a) {nombre},\\n\\nSe adjunta su estado de cuenta con fecha de corte {fecha_corte.isoformat()}.\\n\\nSaludos,\\nRapiCredit"'
new_line = 'email_body = (f"Estimado(a) {nombre},\\n\\nSe adjunta su estado de cuenta con fecha de corte {fecha_corte.isoformat()}.\\n\\nSaludos,\\nRapiCredit")'

if old_line in content:
    content = content.replace(old_line, new_line, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed: email_body line")
else:
    # Try without backslash r n
    old2 = 'email_body = (\n                f"Estimado(a) {nombre},'
    if old2 in content:
        content = content.replace(
            old2,
            'email_body = (f"Estimado(a) {nombre},',
            1
        )
        # Also need to close the string and paren - find the next " and add ")"
        import re
        content = re.sub(
            r'(email_body = \(f"Estimado\(a\) \{nombre\},.*?Saludos,\\nRapiCredit)"\s*\n\s*send_email)',
            r'\1")\n            send_email',
            content,
            count=1,
            flags=re.DOTALL
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Fixed: email_body (variant 2)")
    else:
        print("Pattern not found - check file manually")
