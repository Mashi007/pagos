# Add explicit modo pruebas / producción to docstring in notificaciones_tabs.py
path = r"app\api\v1\endpoints\notificaciones_tabs.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old_doc = '''    """
    Env?a por Email y/o WhatsApp por cada item. Respeta reglas de negocio:
    - modo_pruebas (desde config): si True y email_pruebas v?lido, TODOS los emails van SOLO a ese correo (no a clientes).
    - config_envios (desde BD): si tipo tiene habilitado=false no se env?a; CCO del tipo se env?a como BCC (copia oculta).
    - Si tipo tiene plantilla_id en config, se usa asunto/cuerpo de esa plantilla (con variables sustituidas).
    - Email desde Configuraci?n > Email (holder sincronizado con BD antes de enviar).
    - WhatsApp desde Configuraci?n > WhatsApp (send_whatsapp_text) cuando el item tiene tel?fono.
    """'''

new_doc = '''    """
    Envía por Email y/o WhatsApp por cada item. Respeta reglas de negocio:

    Modo pruebas (modo_pruebas=True y email_pruebas válido):
    - Toma la plantilla de email y los 2 adjuntos PDF (carta cobranza + adjuntos fijos) para realizar prueba test real.
    - Variables en plantilla/cuerpo se dejan como placeholders ({{nombre}}, etc.); el PDF usa contexto placeholder.
    - Todos los correos van SOLO al email de pruebas (no a clientes).

    Modo producción:
    - Toma de las listas específicas por pestaña (previas, día pago, retrasadas, prejudicial, mora 90+).
    - Sustituye variables por datos reales (cliente, cuota, etc.) en asunto/cuerpo y en el PDF.
    - Envía al correo real de cada cliente (+ CCO si está configurado).

    Además: config_envios (desde BD) habilitado/CCO por tipo; Email desde Configuración > Email; WhatsApp si hay teléfono.
    """'''

# Try with original encoding (possible ? = í)
if old_doc in c:
    c = c.replace(old_doc, new_doc)
else:
    # Try without fixing the ? character
    old_alt = old_doc.replace("?", "i")  # Envía, válido, etc.
    if "modo_pruebas (desde config)" in c and "TODOS los emails van SOLO" in c:
        start = c.find('    """')
        end = c.find('    """', start + 4) + 4
        if end > start:
            c = c[:start] + new_doc + c[end:]
        else:
            print("Could not find docstring boundaries")
            exit(1)
    else:
        print("Docstring not found as expected")
        exit(1)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Docstring updated: modo pruebas = plantilla + 2 PDFs test real; producción = listas + datos reales")
