# -*- coding: utf-8 -*-
"""Merge redesigned generar_pdf_estado_cuenta into estado_cuenta_pdf.py. Run from backend/."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SVC = ROOT / "app" / "services" / "estado_cuenta_pdf.py"
BODY = ROOT / "_ec_generar_body.py"


def patch_module_colors(text: str) -> str:
    old = """# Colores RapiCredit (azul corporativo, naranja acento)

COLOR_HEADER = "#1e3a5f"

COLOR_ACCENT = "#c4a35a"

COLOR_HEADER_BG = "#1e3a5f"

COLOR_ROW_ALT = "#f8fafc"

COLOR_BORDER = "#e2e8f0"

COLOR_TEXT_MUTED = "#64748b"
"""
    new = """# Paleta documento (legible en impresion y pantalla)

COLOR_HEADER = "#0c2444"

COLOR_ACCENT = "#b8942e"

COLOR_HEADER_BG = "#0f2d52"

COLOR_ROW_ALT = "#f1f5f9"

COLOR_BORDER = "#cbd5e1"

COLOR_TEXT_MUTED = "#64748b"

COLOR_SURFACE = "#f8fafc"
"""
    if old not in text:
        return text
    return text.replace(old, new, 1)


def main() -> None:
    full = SVC.read_text(encoding="utf-8")
    full = patch_module_colors(full)
    lines = full.splitlines(keepends=True)
    head = "".join(lines[:44])
    tail = "".join(lines[735:])
    body = BODY.read_text(encoding="utf-8")
    if not body.endswith("\n"):
        body += "\n"
    SVC.write_text(head + body + tail, encoding="utf-8")
    print("merged", SVC)


if __name__ == "__main__":
    main()
