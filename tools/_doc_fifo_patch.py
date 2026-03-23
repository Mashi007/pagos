# -*- coding: utf-8 -*-
"""Parche acotado: docs listados + sql/README."""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_sql_readme() -> None:
    p = ROOT / "sql" / "README.md"
    t = p.read_text(encoding="utf-8")
    t2 = """# Scripts SQL y verificaciones

## Verificacion cascada (pagos a cuotas en orden)

Archivos en disco pueden conservar el prefijo `verificar_fifo_*` (historico). La semantica es **cascada** (orden por numero de cuota).

- **verificar_fifo_cuotas.sql** — Consultas de verificacion: resumen, detalle y resultado global. Solo lectura (SELECT).
- **verificar_fifo_resumen_por_prestamo.sql** — Resumen por prestamo: cuota sin completar y lista de cuotas posteriores con pago.
- **run_verificar_cascada.py** — Wrapper Python: pide escribir `fin` antes de ejecutar (usa `verificar_cascada` en el backend).
- **run_verificar_fifo.py** — Compat: redirige al wrapper anterior.
- **run_verificar_fifo.ps1** — Wrapper PowerShell: pide escribir `fin` antes de ejecutar la verificacion (usa `psql`).

Ejecucion con confirmacion: no se ejecuta la verificacion hasta que escribas la palabra **fin**.

"""
    if t.strip() != t2.strip():
        p.write_text(t2, encoding="utf-8", newline="\n")
        print("patched", p.relative_to(ROOT))


def patch_correccion_masiva() -> None:
    p = ROOT / "docs" / "CORRECCION_MASIVA_PAGOS_PAGADO_SIN_CUOTA_PAGOS.md"
    t = p.read_text(encoding="utf-8")
    t2 = t.replace("_estado_pago_tras_aplicar_fifo", "_estado_pago_tras_aplicar_cascada")
    if t2 != t:
        p.write_text(t2, encoding="utf-8", newline="\n")
        print("patched", p.relative_to(ROOT))


def patch_implementacion_items() -> None:
    p = ROOT / "IMPLEMENTACION_ITEMS_1_2_4.md"
    t = p.read_text(encoding="utf-8")
    t2 = t.replace(
        "v_alert_fifo_violacion                  -- Cuota posterior pagada sin pagar anterior",
        "v_alert_cascada_violacion               -- (hist. v_alert_fifo_violacion) Cuota posterior pagada sin pagar anterior",
    )
    if t2 != t:
        p.write_text(t2, encoding="utf-8", newline="\n")
        print("patched", p.relative_to(ROOT))


def patch_verificacion_cuotas_literal() -> None:
    p = ROOT / "VERIFICACION_FIFO_CUOTAS.md"
    t = p.read_text(encoding="utf-8")
    t2 = t.replace("'TEST_FIFO_001'", "'TEST_CASCADA_001'")
    if t2 != t:
        p.write_text(t2, encoding="utf-8", newline="\n")
        print("patched", p.relative_to(ROOT))


def patch_resumen_fifo() -> None:
    p = ROOT / "RESUMEN_FIFO_VERIFICACION.md"
    t = p.read_text(encoding="utf-8")
    t2 = t.replace("### 1. **VERIFICACION_FIFO_CUOTAS.md**", "### 1. **VERIFICACION_FIFO_CUOTAS.md** (verificacion en cascada)")
    t2 = t2.replace("### 2. **test_fifo_verificacion.py**", "### 2. **test_cascada_verificacion.py** (si existe; nombre hist. test_fifo_verificacion.py)")
    if t2 != t:
        p.write_text(t2, encoding="utf-8", newline="\n")
        print("patched", p.relative_to(ROOT))


def main() -> None:
    patch_sql_readme()
    patch_correccion_masiva()
    patch_implementacion_items()
    patch_verificacion_cuotas_literal()
    patch_resumen_fifo()


if __name__ == "__main__":
    main()
