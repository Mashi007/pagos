#!/usr/bin/env python3
"""Rellena Email y Teléfono en hoja Drive de mora desde clientes (por cédula).

Uso (en Render shell o con DATABASE_URL + credenciales Google):
  cd backend
  python tools/_rellenar_contacto_hoja_mora.py --apply
  python tools/_rellenar_contacto_hoja_mora.py --dry-run
  python tools/_rellenar_contacto_hoja_mora.py --csv-out contacto_hoja.csv

La hoja debe estar compartida con la cuenta de servicio Google (Editor).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.services.hoja_mora_contacto_sync import (
    DEFAULT_SHEET_ID,
    generar_csv_contacto_hoja,
    sincronizar_contacto_hoja_mora,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Email/teléfono en hoja mora Drive")
    p.add_argument(
        "--sheet-id",
        default=DEFAULT_SHEET_ID,
        help=f"ID Google Sheet (default: {DEFAULT_SHEET_ID})",
    )
    p.add_argument("--tab", default=None, help="Nombre pestaña (opcional)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo contar matches; no escribe en Drive",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Escribe columnas E (Email) y F (Teléfono) en la hoja",
    )
    p.add_argument(
        "--csv-out",
        metavar="FILE",
        help="Genera CSV cédula,email,teléfono (alternativa manual)",
    )
    args = p.parse_args()

    db = SessionLocal()
    try:
        if args.csv_out:
            csv_text = generar_csv_contacto_hoja(db, spreadsheet_id=args.sheet_id)
            Path(args.csv_out).write_text(csv_text, encoding="utf-8-sig")
            print(f"CSV -> {args.csv_out}")
            return 0

        if not args.apply and not args.dry_run:
            print("Indique --apply, --dry-run o --csv-out FILE")
            return 2

        stats = sincronizar_contacto_hoja_mora(
            db,
            spreadsheet_id=args.sheet_id,
            tab_name=args.tab,
            dry_run=bool(args.dry_run or not args.apply),
        )
        for k, v in stats.items():
            print(f"{k}: {v}")
        if stats.get("escrito"):
            print("OK: columnas E–F actualizadas en la hoja.")
        elif args.dry_run:
            print("Dry-run: no se escribió en Drive.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
