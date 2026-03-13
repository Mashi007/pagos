#!/usr/bin/env python3
"""
Parche: error 500 en GET /api/v1/notificaciones/plantilla-pdf-cobranza/preview
Causa: la plantilla guardada es un documento HTML completo (DOCTYPE, html, head, style, body).
ReportLab paraparser solo acepta un subconjunto (b, i, u, br/, font) y falla con "No content allowed in br tag".
Solución: extraer solo el contenido de <body> y normalizar <br> a <br/> antes de pasar a Paragraph.
"""
import os
import re

PATH = os.path.join(os.path.dirname(__file__), "backend", "app", "services", "carta_cobranza_pdf.py")


def main():
    if not os.path.isfile(PATH):
        print("No encontrado:", PATH)
        return
    with open(PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1) Insertar _extraer_cuerpo_si_html_completo justo antes de _html_para_reportlab
    marker_extraer = 'def _html_para_reportlab(texto: str) -> str:\n    """\n    Convierte HTML con div/p/span/clases'
    bloque_extraer = '''def _extraer_cuerpo_si_html_completo(texto: str) -> str:
    """
    Si el texto es un documento HTML completo (DOCTYPE/html/head/body),
    devuelve solo el contenido del body para que ReportLab no falle.
    ReportLab paraparser no acepta <!DOCTYPE>, <html>, <head>, <style>, etc.
    """
    if not texto or not texto.strip():
        return texto
    t = texto.strip()
    if re.search(r"<!DOCTYPE\\\\s+html", t, re.IGNORECASE) or re.search(r"<html[\\\\s>]", t, re.IGNORECASE):
        body_match = re.search(
            r"<body\\\\s[^>]*>(.*)</body\\\\s*>",
            t,
            re.IGNORECASE | re.DOTALL,
        )
        if body_match:
            t = body_match.group(1)
        else:
            body_match = re.search(r"<body>(.*)</body>", t, re.IGNORECASE | re.DOTALL)
            if body_match:
                t = body_match.group(1)
            else:
                t = re.sub(r"<head\\\\s[^>]*>.*?</head\\\\s*>", "", t, flags=re.IGNORECASE | re.DOTALL)
                t = re.sub(r"<head>.*?</head>", "", t, flags=re.IGNORECASE | re.DOTALL)
                t = re.sub(r"<!DOCTYPE[^>]*>", "", t, flags=re.IGNORECASE)
                t = re.sub(r"<html\\\\s[^>]*>", "", t, flags=re.IGNORECASE)
                t = re.sub(r"</html\\\\s*>", "", t, flags=re.IGNORECASE)
    return t


def _html_para_reportlab(texto: str) -> str:
    """
    Convierte HTML con div/p/span/clases'''

    if "_extraer_cuerpo_si_html_completo" in content:
        print("Ya aplicado: _extraer_cuerpo_si_html_completo existe.")
    elif "def _html_para_reportlab(texto: str) -> str:" in content:
        # Insertar función y modificar inicio de _html_para_reportlab
        content = content.replace(
            'def _html_para_reportlab(texto: str) -> str:\n    """\n    Convierte HTML con div/p/span/clases a un formato que ReportLab Paragraph acepta.\n    ReportLab solo soporta <b>, <i>, <u>, <br/>, <font>, etc. No soporta <div>, <p>, class, style.\n    Se convierten bloques a saltos de l',
            '''def _extraer_cuerpo_si_html_completo(texto: str) -> str:
    """
    Si el texto es un documento HTML completo (DOCTYPE/html/head/body),
    devuelve solo el contenido del body para que ReportLab no falle.
    ReportLab paraparser no acepta <!DOCTYPE>, <html>, <head>, <style>, etc.
    """
    if not texto or not texto.strip():
        return texto
    t = texto.strip()
    if re.search(r"<!DOCTYPE\\s+html", t, re.IGNORECASE) or re.search(r"<html[\\s>]", t, re.IGNORECASE):
        body_match = re.search(
            r"<body\\s[^>]*>(.*)</body\\s*>",
            t,
            re.IGNORECASE | re.DOTALL,
        )
        if body_match:
            t = body_match.group(1)
        else:
            body_match = re.search(r"<body>(.*)</body>", t, re.IGNORECASE | re.DOTALL)
            if body_match:
                t = body_match.group(1)
            else:
                t = re.sub(r"<head\\s[^>]*>.*?</head\\s*>", "", t, flags=re.IGNORECASE | re.DOTALL)
                t = re.sub(r"<head>.*?</head>", "", t, flags=re.IGNORECASE | re.DOTALL)
                t = re.sub(r"<!DOCTYPE[^>]*>", "", t, flags=re.IGNORECASE)
                t = re.sub(r"<html\\s[^>]*>", "", t, flags=re.IGNORECASE)
                t = re.sub(r"</html\\s*>", "", t, flags=re.IGNORECASE)
    return t


def _html_para_reportlab(texto: str) -> str:
    """
    Convierte HTML con div/p/span/clases a un formato que ReportLab Paragraph acepta.
    ReportLab solo soporta <b>, <i>, <u>, <br/>, <font>, etc. No soporta <div>, <p>, class, style.
    Se convierten bloques a saltos de l''',
            1,
        )
        if "_extraer_cuerpo_si_html_completo" not in content:
            print("No se pudo insertar (reemplazo exacto falló).")
            return
        # Añadir llamada y normalización de <br> al inicio del cuerpo de _html_para_reportlab
        old_body_start = '''    if not texto or not texto.strip():
        return texto
    t = texto
    # Quitar comentarios HTML'''
        new_body_start = '''    if not texto or not texto.strip():
        return texto
    t = _extraer_cuerpo_si_html_completo(texto)
    # Normalizar <br> a <br/> (ReportLab: "No content allowed in br tag" si no es self-closing)
    t = re.sub(r"<br\\s*/?\\s*>", "<br/>", t, flags=re.IGNORECASE)
    # Quitar comentarios HTML'''
        if new_body_start in content:
            print("Cuerpo de _html_para_reportlab ya actualizado.")
        elif old_body_start in content:
            content = content.replace(old_body_start, new_body_start, 1)
            print("Cuerpo de _html_para_reportlab actualizado (extracción body + <br/>).")
        else:
            print("No se encontró el bloque 'if not texto or not texto.strip()' en _html_para_reportlab.")
        with open(PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("Parche aplicado en", PATH)
    else:
        print("No se encontró def _html_para_reportlab en el archivo.")


if __name__ == "__main__":
    main()
