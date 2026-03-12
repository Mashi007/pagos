path = r"app\api\v1\endpoints\notificaciones_tabs.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
idx = c.find("def _enviar_correos_items")
start = c.find('    """', idx)
end = c.find('    """', start + 5) + 5
new_doc = '    """\n    Envia por Email y/o WhatsApp por cada item.\n\n    Modo pruebas: plantilla email + 2 adjuntos PDF para prueba test real; variables como placeholders; correo solo a email_pruebas.\n    Modo produccion: listas por pestana; variables sustituidas por datos reales; envio a clientes.\n    """'
c = c[:start] + new_doc + c[end:]
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK")
