# -*- coding: utf-8 -*-
"""Aplica parches fifo->cascada en archivos clave (ejecutar desde repo)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_prestamos() -> None:
    p = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
    t = p.read_text(encoding="utf-8")
    o = t
    o = o.replace(
        "class ReaplicarFifoMasivaBody(BaseModel):\n"
        '    """Lista de prestamo_id a reaplicar en cascada (reset cuota_pagos + aplicar de nuevo). Maximo 500."""\n\n'
        "    prestamo_ids: List[int]",
        "class ReaplicarCascadaMasivaBody(BaseModel):\n"
        '    """Lista de prestamo_id a reaplicar en cascada (reset cuota_pagos + aplicar de nuevo). Maximo 500."""\n\n'
        "    prestamo_ids: List[int]\n\n\n"
        "# Compat: nombre historico del body (OpenAPI / clientes antiguos).\n"
        "ReaplicarFifoMasivaBody = ReaplicarCascadaMasivaBody",
    )
    o = o.replace(
        "@router.post(\"/{prestamo_id}/reaplicar-cascada-aplicacion\", response_model=dict)\n"
        "def reaplicar_fifo_aplicacion_prestamo(",
        "@router.post(\"/{prestamo_id}/reaplicar-cascada-aplicacion\", response_model=dict)\n"
        "def reaplicar_cascada_aplicacion_prestamo(",
    )
    o = o.replace(
        '        logger.exception("reaplicar-fifo-aplicacion prestamo_id=%s: %s", prestamo_id, e)\n'
        "        raise HTTPException(status_code=500, detail=str(e))\n\n\n"
        '@router.post("/reaplicar-fifo-aplicacion-masiva"',
        '        logger.exception("reaplicar-cascada-aplicacion prestamo_id=%s: %s", prestamo_id, e)\n'
        "        raise HTTPException(status_code=500, detail=str(e))\n\n\n"
        "# Compat: nombre de handler historico (importaciones / tests).\n"
        "reaplicar_fifo_aplicacion_prestamo = reaplicar_cascada_aplicacion_prestamo\n\n\n"
        '@router.post("/reaplicar-fifo-aplicacion-masiva"',
    )
    o = o.replace(
        "def reaplicar_fifo_aplicacion_masiva(\n"
        "    body: ReaplicarFifoMasivaBody,",
        "def reaplicar_cascada_aplicacion_masiva(\n"
        "    body: ReaplicarCascadaMasivaBody,",
    )
    o = o.replace(
        "    Igual que /{prestamo_id}/reaplicar-cascada-aplicacion (o ...-fifo-...) pero para varios prestamos.",
        "    Igual que /{prestamo_id}/reaplicar-cascada-aplicacion (ruta legacy ...-fifo-... conservada) pero para varios prestamos.",
    )
    o = o.replace(
        '            logger.exception("reaplicar-fifo-masiva prestamo_id=%s: %s", pid, e)',
        '            logger.exception("reaplicar-cascada-masiva prestamo_id=%s: %s", pid, e)',
    )
    o = o.replace(
        "def reaplicar_cascada_aplicacion_masiva(\n",
        "def reaplicar_cascada_aplicacion_masiva(\n",
    )
    if o == t:
        print("prestamos: sin cambios (ya aplicado o texto distinto)")
    else:
        p.write_text(o, encoding="utf-8", newline="\n")
        print("prestamos: OK")


def patch_pagos_cohorte_msg() -> None:
    p = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
    t = p.read_text(encoding="utf-8")
    o = t
    o = o.replace(
        'raise HTTPException(status_code=400, detail="cohorte debe ser todos, fifo (alias: cascada), o sin_cupo")',
        'raise HTTPException(status_code=400, detail="cohorte debe ser todos, cascada (alias: fifo), o sin_cupo")',
    )
    o = o.replace(
        "sin_cupo: como cascada/fifo y sin cupo aplicable en cuotas PENDIENTE/MORA/PARCIAL.",
        "sin_cupo: como cascada (alias fifo) y sin cupo aplicable en cuotas PENDIENTE/MORA/PARCIAL.",
    )
    if o != t:
        p.write_text(o, encoding="utf-8", newline="\n")
        print("pagos cohorte msg: OK")
    else:
        print("pagos cohorte msg: sin cambios")


def patch_reaplicacion_service() -> None:
    p = ROOT / "backend" / "app" / "services" / "pagos_cuotas_reaplicacion.py"
    t = p.read_text(encoding="utf-8")
    o = t.replace(
        "- reset_y_reaplicar_fifo_prestamo: borra articulacion, resetea cuotas y vuelve a aplicar pagos conciliados.",
        "- reset_y_reaplicar_cascada_prestamo: borra articulacion, resetea cuotas y vuelve a aplicar pagos conciliados.",
    )
    o = o.replace(
        "reconstruir_cascada_fifo_prestamo = reset_y_reaplicar_cascada_prestamo",
        "reconstruir_cascada_prestamo = reset_y_reaplicar_cascada_prestamo\n"
        "# Compat: nombre historico con sufijo fifo.\n"
        "reconstruir_cascada_fifo_prestamo = reset_y_reaplicar_cascada_prestamo",
    )
    if o != t:
        p.write_text(o, encoding="utf-8", newline="\n")
        print("pagos_cuotas_reaplicacion: OK")
    else:
        print("pagos_cuotas_reaplicacion: sin cambios")


def bulk_text_replace() -> None:
    """Reemplazo conservador en md/sql/ps1/py fuera de preserves."""
    skip_dirs = {"node_modules", ".git", ".venv", ".venv_new", "__pycache__", "dist", ".mypy_cache", ".next"}
    exts = {".md", ".sql", ".txt", ".ps1", ".yaml", ".yml"}
    changed = 0
    for dp, dns, fs in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in skip_dirs]
        if any(x in dp for x in skip_dirs):
            continue
        for f in fs:
            if f.endswith(".pyc") or "package-lock" in f:
                continue
            suf = Path(f).suffix
            if suf not in exts:
                continue
            fp = Path(dp) / f
            try:
                raw = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = raw.splitlines(keepends=True)
            out: list[str] = []
            mod = False
            for line in lines:
                nl = transform_doc_line(line)
                if nl != line:
                    mod = True
                out.append(nl)
            if mod:
                fp.write_text("".join(out), encoding="utf-8", newline="\n")
                changed += 1
                print("bulk:", fp.relative_to(ROOT))
    print("bulk files_changed", changed)


def transform_doc_line(line: str) -> str:
    s = line
    # No tocar URLs/paths con -fifo- en SQL referencias
    if "reaplicar-fifo" in s and "router" not in s:
        pass
    # Preservar literales de cohorte en SQL si aparecen
    if 'c = "fifo"' in s.strip():
        return line
    if 'if c not in ("todos", "fifo"' in s:
        return line
    out = s
    out = re.sub(r"\bFIFO\b", "Cascada", out)
    out = re.sub(r"\bFifo\b", "Cascada", out)
    # fifo como palabra suelta (no parte de identificador con guion)
    out = re.sub(r"(?<![\w-])fifo(?![\w-])", "cascada", out, flags=re.IGNORECASE)
    return out


def fix_tools_script() -> None:
    p = ROOT / "tools" / "reemplazar_fifo_por_cascada_global.py"
    if not p.exists():
        return
    t = p.read_text(encoding="utf-8")
    if "import os\nfrom pathlib" not in t and "import os\n\nfrom pathlib" not in t:
        t = t.replace("import re\nfrom pathlib", "import os\nimport re\nfrom pathlib")
        t = t.replace("def iter_files():\n    for dp, dns, fs in os.walk(ROOT):", "def iter_files():\n    import os\n\n    for dp, dns, fs in os.walk(ROOT):")
        # remove duplicate import inside iter_files if we added top level - simplify
    p.write_text(t, encoding="utf-8", newline="\n")
    print("tools script: revisado")


if __name__ == "__main__":
    import os  # noqa: PLC0415

    patch_prestamos()
    patch_pagos_cohorte_msg()
    patch_reaplicacion_service()
    bulk_text_replace()
