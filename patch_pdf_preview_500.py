#!/usr/bin/env python3
"""
Parche para corregir el error 500 en GET /api/v1/notificaciones/plantilla-pdf-cobranza/preview.
Causa: ReportLab con fuente Helvetica no puede renderizar emoji/Unicode del footer.
Aplica: sanitización de texto para PDF y mensaje de error más útil en el preview.
"""
import os

BACKEND_SERVICES = os.path.join(
    os.path.dirname(__file__), "backend", "app", "services", "carta_cobranza_pdf.py"
)
BACKEND_NOTIF = os.path.join(
    os.path.dirname(__file__), "backend", "app", "api", "v1", "endpoints", "notificaciones.py"
)


def patch_carta_cobranza_pdf():
    path = BACKEND_SERVICES
    if not os.path.isfile(path):
        print("No encontrado:", path)
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1) Añadir función de sanitización después de AZUL/NARANJA/GRIS
    marker = 'GRIS_TEXTO = "#444444"\n\n\ndef _format_fecha'
    if "_sanitize_for_reportlab" in content:
        print("carta_cobranza_pdf.py ya parcheado (sanitize).")
    elif marker in content:
        sanitize_block = '''GRIS_TEXTO = "#444444"


def _sanitize_for_reportlab(text: Optional[str]) -> str:
    """
    Asegura que el texto sea renderizable por ReportLab con Helvetica (Latin-1).
    Reemplaza emoji y caracteres que no tiene la fuente por equivalentes ASCII.
    """
    if not text or not isinstance(text, str):
        return ""
    replacements = [
        ("\\u2709", " "),   # envelope
        ("\\u2706", " "),   # telephone
        ("\\U0001f4cd", " "),  # round pushpin
        ("\\U0001f4de", " "),  # telephone
        ("\\U0001f4e7", " "),  # e-mail
        ("\\u260e", " "),   # black phone
        ("\\u2708", " "),   # airplane
    ]
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    result = "".join(
        c for c in result
        if ord(c) < 0x100 or c in "\u00c0\u00c1\u00c2\u00c3\u00c8\u00c9\u00ca\u00cc\u00cd\u00d1\u00d2\u00d3\u00d9\u00da\u00e0\u00e1\u00e2\u00e3\u00e8\u00e9\u00ea\u00ec\u00ed\u00f1\u00f2\u00f3\u00f9\u00fa\u00bf\u00a1"
    )
    return result


def _format_fecha'''
        content = content.replace(marker, sanitize_block, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Añadida _sanitize_for_reportlab en carta_cobranza_pdf.py")
    else:
        print("No se encontró el punto de inserción en carta_cobranza_pdf.py")
        return False

    # 2) En build_pdf_bytes, sanitizar textos que van a Paragraph (footer y slogan)
    # Footer dir: Paragraph(... "?? C.C ... ? info@ ..."
    old_footer = '''    footer_dir = Table([[
        Paragraph(
            "?? C.C Profesional Guacara Plaza, Nivel PB, Local PB-12. Guacara, Carabobo.  "
            "? info@rapicreditca.com  ?? rapicreditca.com  ?? rapicreditca  ?? 0412 314 66 89",
            s_footer_dir,
        )
    ]], colWidths=[16 * cm])'''
    new_footer = '''    footer_dir = Table([[
        Paragraph(
            _sanitize_for_reportlab(
                "C.C Profesional Guacara Plaza, Nivel PB, Local PB-12. Guacara, Carabobo.  "
                "info@rapicreditca.com  rapicreditca.com  rapicreditca  0412 314 66 89"
            ),
            s_footer_dir,
        )
    ]], colWidths=[16 * cm])'''
    if new_footer in content:
        print("Footer ya sanitizado.")
    elif old_footer in content:
        content = content.replace(old_footer, new_footer, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Footer reemplazado por versión sin emoji.")
    else:
        # Buscar variante con otros caracteres
        if "footer_dir = Table" in content and "s_footer_dir" in content:
            import re
            # Sanitizar cualquier Paragraph del footer_dir
            content = re.sub(
                r'(footer_dir = Table\(\[\[\s*Paragraph\(\s*)"([^"]+)"(\s*,\s*s_footer_dir)',
                lambda m: m.group(1) + '"' + _sanitize_simple(m.group(2)) + '"' + m.group(3),
                content,
                count=1,
            )
            def _sanitize_simple(s):
                for a, b in [("\u2709", " "), ("\U0001f4cd", " "), ("\U0001f4de", " "), ("\U0001f4e7", " "), ("\u260e", " "), ("\u2706", " "), ("\u2708", " ")]:
                    s = s.replace(a, b)
                return "".join(c for c in s if ord(c) < 0x100 or c in "\u00c0\u00e0\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00bf\u00a1")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print("Footer sanitizado por regex.")
        else:
            print("No se encontró bloque footer_dir exacto; revisar manualmente.")

    # 3) Sanitizar cuerpo/clausula/firma antes de pasarlos a Paragraph (en build_pdf_bytes no, se hace en generar_*)
    # En generar_carta_cobranza_pdf, sanitizar después de _html_para_reportlab
    gen_marker = "cuerpo = _html_para_reportlab(cuerpo or \"\")"
    if "cuerpo = _sanitize_for_reportlab(_html_para_reportlab" in content:
        print("Cuerpo/clausula/firma ya sanitizados.")
    elif gen_marker in content:
        content = content.replace(
            "cuerpo = _html_para_reportlab(cuerpo or \"\")",
            "cuerpo = _sanitize_for_reportlab(_html_para_reportlab(cuerpo or \"\"))",
            1,
        )
        content = content.replace(
            "clausula = _html_para_reportlab(clausula or \"\")",
            "clausula = _sanitize_for_reportlab(_html_para_reportlab(clausula or \"\"))",
            1,
        )
        content = content.replace(
            "firma_plantilla = _html_para_reportlab(firma_raw or \"\")",
            "firma_plantilla = _sanitize_for_reportlab(_html_para_reportlab(firma_raw or \"\"))",
            1,
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Cuerpo, cláusula y firma pasan por _sanitize_for_reportlab.")

    # 4) En build_pdf_bytes, sanitizar monto_cuotas_html y clausula y firma_plantilla al usarlos
    if "Paragraph(_sanitize_for_reportlab(monto_cuotas_html)" in content or "Paragraph(monto_cuotas_html" not in content:
        pass  # ya hecho o estructura distinta
    else:
        content = content.replace(
            "story.append(Paragraph(monto_cuotas_html, s_body))",
            "story.append(Paragraph(_sanitize_for_reportlab(monto_cuotas_html), s_body))",
            1,
        )
        content = content.replace(
            "story.append(Paragraph(clausula, s_clausula_texto))",
            "story.append(Paragraph(_sanitize_for_reportlab(clausula), s_clausula_texto))",
            1,
        )
        if "story.append(Paragraph(firma_plantilla.strip()" in content:
            content = content.replace(
                "story.append(Paragraph(firma_plantilla.strip(), s_body))",
                "story.append(Paragraph(_sanitize_for_reportlab(firma_plantilla.strip()), s_body))",
                1,
            )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Paragraphs de cuerpo, cláusula y firma sanitizados en build_pdf_bytes.")

    return True


def patch_notificaciones_preview():
    path = BACKEND_NOTIF
    if not os.path.isfile(path):
        print("No encontrado:", path)
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Incluir mensaje del error en el 500 para facilitar diagnóstico (solo el mensaje, no el traceback)
    old = '''    except Exception as e:
        logger.exception("preview_plantilla_pdf_cobranza: %s", e)
        raise HTTPException(status_code=500, detail="Error al generar la vista previa del PDF")'''
    new = '''    except Exception as e:
        logger.exception("preview_plantilla_pdf_cobranza: %s", e)
        detail = "Error al generar la vista previa del PDF"
        if getattr(e, "args", None):
            detail = f"{detail}: {str(e.args[0])[:200]}"
        raise HTTPException(status_code=500, detail=detail)'''
    if new in content:
        print("notificaciones.py preview ya parcheado.")
    elif old in content:
        content = content.replace(old, new, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Preview endpoint: detalle de error añadido en 500.")
    else:
        print("No se encontró bloque except del preview en notificaciones.py.")
    return True


if __name__ == "__main__":
    patch_carta_cobranza_pdf()
    patch_notificaciones_preview()
    print("Listo.")
