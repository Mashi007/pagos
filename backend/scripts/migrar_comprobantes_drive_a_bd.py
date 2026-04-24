#!/usr/bin/env python3
"""
Migra comprobantes con enlace a Google Drive (o id suelto) a la BD del sistema.

- Inserta fila en ``pago_comprobante_imagen`` (misma regla que pipeline Gmail: 10 MB, MIME imagen/PDF).
- Actualiza ``pagos.link_comprobante`` con la URL del API (``/api/v1/pagos/comprobante-imagen/{id}``).

Requisitos:
- ``DATABASE_URL`` / .env como el resto del backend.
- Descarga vía Drive API (credenciales Gmail/Informe) y/o descarga anónima ``uc?export=download``
  (solo si el archivo en Drive permite «cualquiera con el enlace»).

Uso (desde la carpeta ``backend``):

  python scripts/migrar_comprobantes_drive_a_bd.py --dry-run
  python scripts/migrar_comprobantes_drive_a_bd.py --execute --limit 50
  python scripts/migrar_comprobantes_drive_a_bd.py --execute --pago-id 12345

No crea tablas nuevas; no requiere SQL de migración de esquema.
Ver ``sql/migracion_comprobantes_drive_candidatos.sql`` para auditar candidatos en PostgreSQL.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

_REPO_ROOT = os.path.dirname(BACKEND)
for _env_name in (".env", ".env.local"):
    _p = os.path.join(_REPO_ROOT, _env_name)
    if os.path.isfile(_p):
        try:
            from dotenv import load_dotenv

            load_dotenv(_p)
        except ImportError:
            pass
        break

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("migrar_comprobantes_drive")


def main() -> int:
    from sqlalchemy import and_, func, not_, or_, select
    from sqlalchemy.orm import Session

    from app.core.database import SessionLocal
    from app.models.pago import Pago
    from app.services.pagos.migracion_comprobante_drive_a_bd import (
        descargar_y_normalizar_comprobante_drive,
        enlace_requiere_migracion_drive_a_bd,
        extraer_google_drive_file_id,
    )
    from app.services.pagos_gmail.comprobante_bd import persistir_comprobante_gmail_en_bd

    ap = argparse.ArgumentParser(description="Migrar links Drive → pago_comprobante_imagen + link API")
    ap.add_argument("--dry-run", action="store_true", help="Solo listar y simular; no escribe BD")
    ap.add_argument("--execute", action="store_true", help="Aplicar cambios (commit por lote)")
    ap.add_argument("--limit", type=int, default=0, help="Máximo de pagos a procesar (0 = sin límite)")
    ap.add_argument("--pago-id", type=int, default=0, help="Solo este id de pago")
    ap.add_argument("--commit-every", type=int, default=10, help="Commit cada N migraciones OK")
    args = ap.parse_args()

    if not args.dry_run and not args.execute:
        logger.error("Indique --dry-run o --execute")
        return 2

    db: Session = SessionLocal()
    ok = 0
    skip = 0
    err = 0
    pending_commit = 0

    try:
        link_sin_slash = and_(
            func.length(func.trim(Pago.link_comprobante)) >= 25,
            not_(Pago.link_comprobante.contains("/")),
        )
        q = (
            select(Pago)
            .where(Pago.link_comprobante.isnot(None))
            .where(not_(Pago.link_comprobante.ilike("%comprobante-imagen%")))
            .where(or_(Pago.link_comprobante.ilike("%drive.google%"), link_sin_slash))
        )
        if args.pago_id:
            q = q.where(Pago.id == int(args.pago_id))
        q = q.order_by(Pago.id.asc())
        rows = db.execute(q).scalars().all()

        processed = 0
        for pago in rows:
            link = (getattr(pago, "link_comprobante", None) or "").strip()
            if not enlace_requiere_migracion_drive_a_bd(link):
                continue

            fid = extraer_google_drive_file_id(link)
            if not fid:
                logger.warning("omitido pago_id=%s sin file_id parseable link=%s…", pago.id, link[:60])
                skip += 1
                continue

            if args.limit and processed >= args.limit:
                break
            processed += 1

            body, mime, derr = descargar_y_normalizar_comprobante_drive(fid)
            if not body or not mime:
                logger.error("pago_id=%s file_id=%s… fallo_descarga=%s", pago.id, fid[:12], derr)
                err += 1
                continue

            if args.dry_run:
                logger.info(
                    "dry-run OK pago_id=%s file_id=%s… bytes=%s mime=%s",
                    pago.id,
                    fid[:12],
                    len(body),
                    mime,
                )
                ok += 1
                continue

            hit = persistir_comprobante_gmail_en_bd(db, body, mime, sha256_hex=None, reuse_por_sha256=None)
            if not hit:
                logger.error("pago_id=%s no_persistido (tamano/MIME pipeline)", pago.id)
                err += 1
                continue

            uid, new_url = hit
            prev = link[:200]
            pago.link_comprobante = new_url
            if getattr(pago, "documento_tipo", None) is None and mime:
                pago.documento_tipo = mime.split("/")[-1][:50] if "/" in mime else None
            nota = (getattr(pago, "notas", None) or "").strip()
            tag = f"[migr_drive_bd {prev[:120]}]"
            if tag not in nota:
                pago.notas = (nota + "\n" + tag).strip() if nota else tag.strip()

            pending_commit += 1
            ok += 1
            db.flush()

            if pending_commit >= max(1, args.commit_every):
                db.commit()
                logger.info("commit lote ok (hasta pago_id=%s)", pago.id)
                pending_commit = 0

        if args.execute and pending_commit:
            db.commit()
            logger.info("commit final")

        if args.dry_run:
            db.rollback()

    except Exception:
        logger.exception("fallo_global")
        db.rollback()
        return 1
    finally:
        db.close()

    logger.info("resumen ok=%s omitidos_parse=%s errores=%s dry_run=%s", ok, skip, err, args.dry_run)
    return 0 if err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
