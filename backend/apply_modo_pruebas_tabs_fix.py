# -*- coding: utf-8 -*-
"""
Aplica en notificaciones_tabs.py:
1. Añadir import de _contexto_cobranza_placeholder desde notificaciones.
2. Corregir la línea rota: separar ctx_pdf y pdf_bytes en dos líneas (quitar el literal `r`n).

Modo pruebas: plantilla email + 2 adjuntos PDF (anexo + fijo) → prueba test real al correo de pruebas.
Modo producción: listas específicas por pestaña, variables sustituidas por datos reales.
"""
import os

FILE = os.path.join(os.path.dirname(__file__), "app", "api", "v1", "endpoints", "notificaciones_tabs.py")

def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Añadir import
    old_import = """from app.api.v1.endpoints.notificaciones import (
    get_notificaciones_tabs_data,
    get_notificaciones_envios_config,
    get_plantilla_asunto_cuerpo,
    build_contexto_cobranza_para_item,
)"""
    new_import = """from app.api.v1.endpoints.notificaciones import (
    get_notificaciones_tabs_data,
    get_notificaciones_envios_config,
    get_plantilla_asunto_cuerpo,
    build_contexto_cobranza_para_item,
    _contexto_cobranza_placeholder,
)"""
    if _contexto_cobranza_placeholder not in content and "build_contexto_cobranza_para_item," in content:
        content = content.replace(old_import, new_import)
        print("Import añadido.")
    else:
        print("Import ya presente o bloque distinto.")

    # 2. Corregir línea con `r`n literal
    broken = 'ctx_pdf = _contexto_cobranza_placeholder() if usar_solo_pruebas else item["contexto_cobranza"]`r`n                        pdf_bytes = generar_carta_cobranza_pdf(ctx_pdf, db=db)'
    fixed = '''ctx_pdf = _contexto_cobranza_placeholder() if usar_solo_pruebas else item["contexto_cobranza"]
                        pdf_bytes = generar_carta_cobranza_pdf(ctx_pdf, db=db)'''
    if broken in content:
        content = content.replace(broken, fixed)
        print("Línea ctx_pdf/pdf_bytes corregida.")
    else:
        # Por si el literal está con otro espaciado
        if "`r`n" in content:
            content = content.replace("`r`n", "\n")
            print("Reemplazado literal `r`n por salto de línea.")
        else:
            print("No se encontró la línea rota (puede estar ya corregida).")

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print("Guardado:", FILE)

if __name__ == "__main__":
    main()
