# -*- coding: utf-8 -*-
"""Apply PDF design: patch colors, merge body, patch __all__. Run from backend/."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SVC = ROOT / "app" / "services" / "estado_cuenta_pdf.py"
BODY = ROOT / "_ec_generar_body.py"


def patch_colors(text: str) -> str:
    new = """# Paleta documento (legible en impresion y pantalla)

COLOR_HEADER = "#0c2444"

COLOR_ACCENT = "#b8942e"

COLOR_HEADER_BG = "#0f2d52"

COLOR_ROW_ALT = "#f1f5f9"

COLOR_BORDER = "#cbd5e1"

COLOR_TEXT_MUTED = "#64748b"

COLOR_SURFACE = "#f8fafc"
"""
    text, n = re.subn(
        r"# Colores RapiCredit.*?\nCOLOR_TEXT_MUTED = \"#64748b\"\s*",
        new + "\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    if n == 0:
        return text
    if '"COLOR_SURFACE"' not in text:
        text = text.replace(
            '"COLOR_ROW_ALT",\n    "COLOR_TEXT_MUTED"',
            '"COLOR_ROW_ALT",\n    "COLOR_SURFACE",\n    "COLOR_TEXT_MUTED"',
            1,
        )
    return text


def fix_body_image() -> None:
    t = BODY.read_text(encoding="utf-8")
    t = t.replace(", kind=\"proportional\")", ")")
    BODY.write_text(t, encoding="utf-8")


def main() -> None:
    fix_body_image()
    full = SVC.read_text(encoding="utf-8")
    full = patch_colors(full)
    lines = full.splitlines(keepends=True)
    head = "".join(lines[:44])
    tail = "".join(lines[735:])
    body = BODY.read_text(encoding="utf-8")
    if not body.endswith("\n"):
        body += "\n"
    SVC.write_text(head + body + tail, encoding="utf-8")
    print("ok", SVC)


if __name__ == "__main__":
    main()
