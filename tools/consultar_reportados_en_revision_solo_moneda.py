#!/usr/bin/env python3
"""
Consulta en BD los pagos reportados que quedaron en revisión porque Gemini
marcó solo divergencia de «Moneda» (típico USDT vs USD en comprobante BINANCE).

IMPORTANTE:
- La validación con Gemini corre UNA SOLA VEZ al enviar el formulario público.
  No hay job que re-evalúe filas antiguas cuando cambias el prompt o el código.
- Por eso los casos capturados antes del ajuste USDT=USD siguen en `en_revision`
  hasta que alguien los apruebe en Cobros o corrija datos.

Uso (desde la raíz del repo, con .env del backend cargado o DATABASE_URL en entorno):

    cd pagos
    python tools/consultar_reportados_en_revision_solo_moneda.py

Opciones:
    --binance     Solo filas con institución BINANCE (insensible a mayúsculas)
    --cedula V123 Buscar por cédula (tipo+número o fragmento)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Raíz repo: .../pagos
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# Cargar .env del backend si existe
try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND / ".env")
except ImportError:
    pass

from sqlalchemy import select, or_  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.pago_reportado import PagoReportado  # noqa: E402


def comentario_solo_moneda(raw: str | None) -> bool:
    if not raw or not str(raw).strip():
        return False
    tokens = []
    for t in str(raw).split(","):
        s = t.strip().lower().rstrip(".;:")
        if s:
            tokens.append(s)
    return bool(tokens) and all(x == "moneda" for x in tokens)


def main() -> None:
    parser = argparse.ArgumentParser(description="Listar pagos_reportados en revisión por solo-Moneda (Gemini).")
    parser.add_argument("--binance", action="store_true", help="Solo BINANCE")
    parser.add_argument("--cedula", type=str, default="", help="Filtrar por cédula (concat tipo+número)")
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: defina DATABASE_URL o configure backend/.env", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        q = select(PagoReportado).where(
            PagoReportado.estado == "en_revision",
            PagoReportado.gemini_coincide_exacto == "false",
        )
        if args.binance:
            q = q.where(PagoReportado.institucion_financiera.ilike("%BINANCE%"))
        if args.cedula:
            c = args.cedula.strip().replace("-", "").replace(" ", "").upper()
            q = q.where(
                or_(
                    PagoReportado.numero_cedula.like(f"%{c}%"),
                    PagoReportado.tipo_cedula.concat(PagoReportado.numero_cedula).like(f"%{c}%"),
                )
            )

        rows = db.execute(q.order_by(PagoReportado.created_at.desc())).scalars().all()
        candidatos = [r for r in rows if comentario_solo_moneda(r.gemini_comentario)]

        print(f"Total en_revision + gemini false: {len(rows)}")
        print(f"Candidatos «solo Moneda» (misma lógica que el backend): {len(candidatos)}")
        print("-" * 100)
        for r in candidatos:
            ced = f"{r.tipo_cedula or ''}{r.numero_cedula or ''}"
            com = (r.gemini_comentario or "").replace("\n", " ")[:120]
            print(
                f"id={r.id}  ref={r.referencia_interna}  {r.nombres[:20]}…  "
                f"cédula={ced}  banco={r.institucion_financiera}  "
                f"{r.monto} {r.moneda}  fecha_pago={r.fecha_pago}  gemini_comentario={com!r}"
            )
        print("-" * 100)
        print(
            "Nota: estos registros NO se actualizan solos. "
            "Apruébelos desde Cobros o espere nuevos envíos (ya con la regla USDT=USD en código)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
