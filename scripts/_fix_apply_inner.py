from pathlib import Path
p = Path(__file__).resolve().parent / "_apply_cobros_mejoras.py"
text = p.read_text(encoding="utf-8")
old = """    if "_prestamos_aprobados_del_cliente" in t:
        print("cobros_publico: already patched")
        return
    # Insert helper after logger = ...
    anchor = 'logger = logging.getLogger(__name__)\\n\\ndef _intentar_importar_reportado_automatico'
    if anchor not in t:
        raise SystemExit("cobros_publico: anchor for helper not found")
    t = t.replace(
        "logger = logging.getLogger(__name__)\\n\\n\\ndef _intentar_importar_reportado_automatico",
        "logger = logging.getLogger(__name__)" + HELPER + "\\n\\ndef _intentar_importar_reportado_automatico",
        1,
    )
    # Fix double newline if we had \\n\\n\\n
    t = t.replace("logger = logging.getLogger(__name__)" + HELPER + "\\n\\n\\ndef _intentar_importar_reportado_automatico", "logger = logging.getLogger(__name__)" + HELPER + "\\n\\ndef _intentar_importar_reportado_automatico", 1)"""
new = """    if "_prestamos_aprobados_del_cliente" in t:
        print("cobros_publico: already patched")
        return
    anchor = "logger = logging.getLogger(__name__)\\n\\ndef _intentar_importar_reportado_automatico"
    if anchor not in t:
        raise SystemExit("cobros_publico: anchor for helper not found")
    t = t.replace(
        anchor,
        "logger = logging.getLogger(__name__)" + HELPER + "\\n\\ndef _intentar_importar_reportado_automatico",
        1,
    )"""
if old not in text:
    raise SystemExit("old block not found in _apply_cobros_mejoras.py")
p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched _apply_cobros_mejoras.py")
