# -*- coding: utf-8 -*-
"""
Reemplazo integral de trazas 'fifo' por 'cascada' en el repo (codigo fuente y docs).

- NO toca: node_modules, .venv, dist, __pycache__, .mypy_cache, .git, *.pyc
- Preserva lineas que contienen valores de API o rutas legacy explicitas (lista PRESERVE_SUBSTRINGS).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    "node_modules",
    ".git",
    ".venv",
    ".venv_new",
    "__pycache__",
    "dist",
    ".mypy_cache",
    ".next",
    "coverage",
}

EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".sql", ".yaml", ".yml", ".txt", ".ps1", ".sh"}

# Si una linea contiene alguno de estos fragmentos, no se modifica (valores wire / compat).
PRESERVE = (
    'cohorte debe ser todos, fifo (alias: cascada)',  # mensaje ya explica alias; opcional
)

# Mejor: preservar asignacion interna tras normalizar
PRESERVE_PREFIXES = (
    'c = "fifo"',
    "c = 'fifo'",
)


def should_skip_line(line: str) -> bool:
    s = line
    if any(p in s for p in PRESERVE):
        return True
    if 'if c not in ("todos", "fifo", "sin_cupo")' in s or "if c not in ('todos', 'fifo', 'sin_cupo')" in s:
        return True
    for p in PRESERVE_PREFIXES:
        if p in s and "cascada" in line.lower() and "fifo" in line:
            pass
    if 'c = "fifo"' in s.strip() or "c = 'fifo'" in s.strip():
        return True
    # Rutas HTTP legacy: mantener path literal para no romper clientes antiguos
    if '@router.post("/{prestamo_id}/reaplicar-fifo-aplicacion"' in s:
        return True
    if '@router.post("/reaplicar-fifo-aplicacion-masiva"' in s:
        return True
    if '"/reaplicar-fifo-aplicacion"' in s or "'/reaplicar-fifo-aplicacion'" in s:
        return True
    return False


def transform_line(line: str) -> str:
    if should_skip_line(line):
        return line
    out = line
    # Identificadores y nombres compuestos (orden importa)
    rep_ident = [
        ("ReaplicarFifoMasivaBody", "ReaplicarCascadaMasivaBody"),
        ("reaplicar_fifo_aplicacion_prestamo", "reaplicar_cascada_aplicacion_prestamo"),
        ("reaplicar_fifo_aplicacion_masiva", "reaplicar_cascada_aplicacion_masiva"),
        ("reset_y_reaplicar_fifo_prestamo", "reset_y_reaplicar_cascada_prestamo"),
        ("_estado_pago_tras_aplicar_fifo", "_estado_pago_tras_aplicar_cascada"),
    ]
    for a, b in rep_ident:
        out = out.replace(a, b)

    # Palabras sueltas / texto (no tocar substrings ya reemplazados en preserve)
    out = re.sub(r"\bFIFO\b", "Cascada", out)
    out = re.sub(r"\bFifo\b", "Cascada", out)
    # fifo como palabra: cuidado con reaplicar-fifo en comentarios -> reemplazar frase completa
    out = re.sub(r"\bfifo\b", "cascada", out)
    return out


def iter_files():
    for dp, dns, fs in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        if any(x in dp for x in SKIP_DIRS):
            continue
        for f in fs:
            if f.endswith(".pyc") or "package-lock" in f:
                continue
            suf = Path(f).suffix
            if suf not in EXT:
                continue
            yield Path(dp) / f


def main() -> None:
    import os

    changed = 0
    for fp in iter_files():
        try:
            raw = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = raw.splitlines(keepends=True)
        new_lines = []
        mod = False
        for line in lines:
            nl = transform_line(line)
            if nl != line:
                mod = True
            new_lines.append(nl)
        if mod:
            fp.write_text("".join(new_lines), encoding="utf-8", newline="\n")
            changed += 1
            print(fp.relative_to(ROOT))
    print("files_changed", changed)


if __name__ == "__main__":
    import os  # noqa: PLC0415

    main()
