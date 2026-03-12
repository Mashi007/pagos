# -*- coding: utf-8 -*-
"""
Comprueba que los archivos .py del backend con texto en español estén en UTF-8.
Ejecutar desde backend/: python tests/check_utf8_spanish.py

Si algún archivo tiene caracteres corruptos (mojibake), re-guardarlo como UTF-8 sin BOM.
"""
import os
import sys

# Caracteres típicos en español (Unicode)
SPANISH_CHARS = "áéíóúñÁÉÍÓÚÑüÜ¿¡"
# Encodings a probar
ENCODINGS = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT, "app")


def has_spanish(s: str) -> bool:
    return any(c in s for c in SPANISH_CHARS)


def check_file(path: str) -> dict:
    """Devuelve {encoding, ok, error}."""
    with open(path, "rb") as f:
        raw = f.read()
    if not raw:
        return {"encoding": None, "ok": True, "error": None}
    # Intentar UTF-8 primero
    try:
        text = raw.decode("utf-8")
        if "\xff" in text or (len(raw) > 3 and raw[:3] == b"\xef\xbb\xbf"):
            return {"encoding": "utf-8-sig", "ok": True, "error": None}
        return {"encoding": "utf-8", "ok": True, "error": None}
    except UnicodeDecodeError as e:
        pass
    # Probablemente no UTF-8
    for enc in ["cp1252", "latin-1"]:
        try:
            raw.decode(enc)
            return {"encoding": enc, "ok": False, "error": "No es UTF-8 (detectado %s). Re-guardar como UTF-8." % enc}
        except Exception:
            pass
    return {"encoding": None, "ok": False, "error": "No se pudo decodificar"}


def main():
    files_with_spanish = []
    problems = []
    for dirpath, _dirnames, filenames in os.walk(APP_DIR):
        for name in filenames:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                result = check_file(path)
                rel = os.path.relpath(path, ROOT)
                problems.append((rel, result["error"] or result["encoding"]))
                continue
            if has_spanish(content):
                files_with_spanish.append(os.path.relpath(path, ROOT))
    # También comprobar endpoints clave
    for rel in ["app/api/v1/endpoints/configuracion.py", "app/api/v1/endpoints/notificaciones_tabs.py", "app/core/deps.py"]:
        path = os.path.join(ROOT, rel)
        if os.path.isfile(path) and rel not in files_with_spanish:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    if has_spanish(f.read()):
                        files_with_spanish.append(rel)
            except Exception:
                pass
    if problems:
        print("Archivos que no son UTF-8 válido:")
        for rel, err in problems:
            print("  %s: %s" % (rel, err))
        sys.exit(1)
    print("OK: Los archivos Python revisados son UTF-8 válidos.")
    if files_with_spanish:
        print("Archivos con texto en español (muestra): %s" % ", ".join(files_with_spanish[:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
