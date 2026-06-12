"""Diagnóstico reserva temporal + pagos por cédula (revisión manual / conciliar)."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cedula", help="Ej. V16370277")
    parser.add_argument("--prestamo-id", type=int, default=None)
    args = parser.parse_args()

    url = (os.getenv("DATABASE_URL") or "").replace("postgres://", "postgresql://", 1)
    if not url:
        print("DATABASE_URL no configurada")
        sys.exit(1)

    engine = create_engine(url)
    ced = args.cedula.strip().upper().replace("-", "")

    with engine.connect() as conn:
        prestamos = conn.execute(
            text(
                """
                SELECT id, estado, cedula
                FROM prestamos
                WHERE UPPER(REPLACE(COALESCE(cedula,''), '-', '')) = :ced
                ORDER BY id
                """
            ),
            {"ced": ced},
        ).mappings().all()
        print(f"\n=== PRESTAMOS ({len(prestamos)}) ===")
        for p in prestamos:
            print(dict(p))

        pid_filter = args.prestamo_id
        print(f"\n=== PAGOS EN CARTERA (tabla pagos) ===")
        q_pagos = """
            SELECT p.id, p.prestamo_id, p.monto_pagado, p.numero_documento,
                   CASE WHEN p.link_comprobante IS NOT NULL AND p.link_comprobante <> '' THEN 'si' ELSE 'no' END AS tiene_link,
                   CASE WHEN p.link_comprobante LIKE '%comprobante-imagen/%' THEN 'bd' 
                        WHEN p.link_comprobante LIKE '%drive%' THEN 'drive'
                        ELSE COALESCE(LEFT(p.link_comprobante, 20), 'no') END AS tipo_link,
                   p.documento_ruta
            FROM pagos p
            JOIN prestamos pr ON pr.id = p.prestamo_id
            WHERE UPPER(REPLACE(COALESCE(pr.cedula,''), '-', '')) = :ced
        """
        params: dict = {"ced": ced}
        if pid_filter:
            q_pagos += " AND p.prestamo_id = :pid"
            params["pid"] = pid_filter
        q_pagos += " ORDER BY p.prestamo_id, p.id"
        pagos = conn.execute(text(q_pagos), params).mappings().all()
        print(f"Total pagos: {len(pagos)}")
        for p in pagos:
            print(dict(p))

        print(f"\n=== RESERVA TEMPORAL revision_manual_conciliacion_reserva ===")
        q_res = """
            SELECT r.id, r.prestamo_id, r.orden, r.pago_id_origen, r.pago_id_recriado,
                   r.ocr_ok, octet_length(r.comprobante_imagen_data) AS bytes,
                   LEFT(COALESCE(r.ocr_error,''), 150) AS ocr_error
            FROM revision_manual_conciliacion_reserva r
            LEFT JOIN prestamos pr ON pr.id = r.prestamo_id
            WHERE UPPER(REPLACE(COALESCE(r.cedula_cliente,''), '-', '')) = :ced
               OR UPPER(REPLACE(COALESCE(pr.cedula,''), '-', '')) = :ced
        """
        if pid_filter:
            q_res += " AND r.prestamo_id = :pid"
        q_res += " ORDER BY r.prestamo_id, r.orden"
        reservas = conn.execute(text(q_res), params).mappings().all()
        print(f"Filas con imagen en temporal: {len(reservas)}")
        for r in reservas:
            print(dict(r))

        print(f"\n=== PAGOS CON ERRORES (no entran a reserva de Conciliar) ===")
        try:
            pce = conn.execute(
                text(
                    """
                    SELECT id, prestamo_id, monto_pagado, numero_documento
                    FROM pagos_con_errores
                    WHERE UPPER(REPLACE(COALESCE(cedula,''), '-', '')) = :ced
                       OR prestamo_id IN (SELECT id FROM prestamos WHERE UPPER(REPLACE(COALESCE(cedula,''), '-', '')) = :ced)
                    ORDER BY id DESC LIMIT 50
                    """
                ),
                {"ced": ced},
            ).mappings().all()
            print(f"Total (max 50): {len(pce)}")
            for row in pce:
                print(dict(row))
        except Exception as e:
            print(f"(tabla no disponible: {e})")

        print(f"\n=== PAGO ORIGEN RESERVA (60279) ===")
        try:
            po = conn.execute(
                text("SELECT id, prestamo_id, numero_documento, link_comprobante FROM pagos WHERE id = 60279")
            ).fetchone()
            print(po)
        except Exception as e:
            print(e)

        print(f"\n=== GMAIL SYNC ITEMS (cedula) ===")
        try:
            gsi = conn.execute(
                text(
                    """
                    SELECT gsi.id, gsi.cedula, gsi.monto, gsi.numero_referencia,
                           CASE WHEN gsi.drive_link IS NOT NULL AND gsi.drive_link <> '' THEN 'si' ELSE 'no' END AS tiene_link
                    FROM pagos_gmail_sync_item gsi
                    WHERE UPPER(REPLACE(COALESCE(gsi.cedula,''), '-', '')) = :ced
                    ORDER BY gsi.id DESC LIMIT 30
                    """
                ),
                {"ced": ced},
            ).mappings().all()
            print(f"Items: {len(gsi)}")
            for row in gsi[:15]:
                print(dict(row))
        except Exception as e:
            print(f"gmail: {e}")

        if pid_filter:
            from app.core.database import SessionLocal
            from app.services.revision_manual_conciliacion_cartera_service import (
                diagnostico_comprobantes_conciliar_prestamo,
            )

            db = SessionLocal()
            try:
                diag = diagnostico_comprobantes_conciliar_prestamo(db, pid_filter)
                print(f"\n=== DIAGNÓSTICO CONCILIAR (prestamo {pid_filter}) ===")
                print(f"total_pagos: {diag.get('total_pagos')}")
                print(f"pagos_con_enlace (cartera): {diag.get('pagos_con_enlace')}")
                print(f"fuentes_total: {diag.get('fuentes_comprobante_total')}")
                print(f"  - cartera: {diag.get('fuentes_pago_cartera')}")
                print(f"  - pagos_con_errores: {diag.get('fuentes_pago_con_error')}")
                print(f"  - gmail_sync: {diag.get('fuentes_gmail_sync')}")
                print(f"imagenes_reservables: {diag.get('pagos_reservables')}")
                print(f"omitidos_sin_bytes: {diag.get('pagos_omitidos_sin_bytes')}")
                for o in diag.get("omitidos") or []:
                    print(f"  omitido pago_id={o.get('pago_id')} ref={o.get('referencia')} err={o.get('error')}")
            finally:
                db.close()


if __name__ == "__main__":
    main()
