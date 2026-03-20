#!/usr/bin/env python3
"""
Respaldo completo de la BD (opción A): pg_dump formato custom (-Fc).

Usa DATABASE_URL desde la variable de entorno o desde .env en la raíz del repo
(misma convención que el backend: DATABASE_URL=postgresql://...).

Requisitos: cliente PostgreSQL (pg_dump) en PATH.

Uso:
  set DATABASE_URL=postgresql://user:pass@host:5432/dbname
  python scripts/backup_bd_opcion_a.py

  # o con .env en la raíz del proyecto que contenga DATABASE_URL=...
  python scripts/backup_bd_opcion_a.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
OUT_DIR = ROOT / "backups"


def load_database_url() -> str:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        return url
    if ENV_FILE.is_file():
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                m = re.match(r"DATABASE_URL\s*=\s*(.+)", s)
                if m:
                    return m.group(1).strip().strip('"').strip("'")
    return ""


def main() -> int:
    url = load_database_url()
    if not url:
        print(
            "ERROR: Defina DATABASE_URL en el entorno o en .env en la raíz del proyecto.",
            file=sys.stderr,
        )
        return 1
    if not shutil.which("pg_dump"):
        print(
            "ERROR: pg_dump no está en PATH. Instale las herramientas cliente de PostgreSQL.",
            file=sys.stderr,
        )
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"backup_antes_regenerar_cuotas_{ts}.dump"

    cmd = ["pg_dump", "-d", url, "-Fc", "-f", str(out)]
    print("Ejecutando pg_dump -Fc →", out)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        return r.returncode

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"OK: {out} ({size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
