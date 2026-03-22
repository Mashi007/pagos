#!/usr/bin/env python3
"""
Carga tasas oficiales (Bs. por 1 USD) por fecha en tasas_cambio_diaria.
Sirve para el backfill de pagos BS cuando falta tasa en la fecha de pago del reporte.

Requisito: DATABASE_URL o .env del backend con la misma variable.

Uso (desde la raíz del repo):

    python tools/cargar_tasas_fechas_pagos_bs.py 2026-03-12=3105.75 2026-03-14=3110.00

O con archivo CSV (UTF-8, sin cabecera o con cabecera fecha,tasa):

    python tools/cargar_tasas_fechas_pagos_bs.py --csv mis_tasas.csv

Cada fila inserta o actualiza (upsert vía servicio) una fecha.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND / ".env")
except ImportError:
    pass


def _parse_pairs(pairs: list[str]) -> list[tuple[date, float]]:
    out: list[tuple[date, float]] = []
    for raw in pairs:
        if "=" not in raw:
            raise SystemExit(f"Formato invalido (use YYYY-MM-DD=tasa): {raw}")
        left, right = raw.split("=", 1)
        d = date.fromisoformat(left.strip())
        tasa = float(right.strip().replace(",", "."))
        if tasa <= 0:
            raise SystemExit(f"Tasa debe ser > 0: {raw}")
        out.append((d, tasa))
    return out


def _load_csv(path: Path) -> list[tuple[date, float]]:
    out: list[tuple[date, float]] = []
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return out
    start = 0
    if (
        len(rows[0]) >= 1
        and rows[0][0].strip().lower() in ("fecha", "date")
    ):
        start = 1
    for row in rows[start:]:
        if len(row) < 2 or not row[0].strip() or row[0].strip().startswith("#"):
            continue
        d = date.fromisoformat(row[0].strip())
        tasa = float(row[1].strip().replace(",", "."))
        if tasa <= 0:
            raise SystemExit(f"Tasa debe ser > 0 en fila: {row}")
        out.append((d, tasa))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Cargar tasas por fecha (backfill BS)")
    parser.add_argument(
        "pairs",
        nargs="*",
        help="Pares fecha=tasa, ej. 2026-03-12=3105.75",
    )
    parser.add_argument("--csv", type=Path, help="CSV con columnas fecha,tasa")
    args = parser.parse_args()

    if args.csv:
        rows = _load_csv(args.csv)
    elif args.pairs:
        rows = _parse_pairs(args.pairs)
    else:
        parser.error("Indique pares fecha=tasa o --csv")

    if not rows:
        print("No hay filas para cargar.")
        return

    from app.core.database import SessionLocal
    from app.services.tasa_cambio_service import guardar_tasa_para_fecha

    db = SessionLocal()
    try:
        for d, tasa in rows:
            guardar_tasa_para_fecha(
                db,
                fecha=d,
                tasa_oficial=tasa,
                usuario_id=None,
                usuario_email="cargar_tasas_fechas_pagos_bs.py",
            )
            print(f"OK {d.isoformat()} tasa={tasa}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
