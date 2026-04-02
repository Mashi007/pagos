"""
Crea el esquema en PostgreSQL para pytest en CI (create_all).
Ejecutar con DATABASE_URL y SECRET_KEY ya definidos en el entorno.
"""
from __future__ import annotations

import os


def main() -> None:
    os.environ.setdefault(
        "SECRET_KEY", "0123456789abcdef0123456789abcdef0123456789ab"
    )
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL requerido para ci_bootstrap_db")

    import app.models  # noqa: F401
    from app.models.pagos_gmail_sync import GmailTemporal  # noqa: F401

    from app.models import Base
    from sqlalchemy import inspect, text

    from app.core.database import engine

    Base.metadata.create_all(bind=engine)
    try:
        insp = inspect(engine)
        if "pagos" in insp.get_table_names():
            col_names = {c["name"] for c in insp.get_columns("pagos")}
            if "link_comprobante" not in col_names:
                with engine.connect() as conn:
                    conn.execute(
                        text(
                            "ALTER TABLE pagos ADD COLUMN link_comprobante TEXT NULL"
                        )
                    )
                    conn.commit()
    except Exception as ex:
        print("[ci_bootstrap_db] aviso link_comprobante:", ex)
    print("[ci_bootstrap_db] schema OK")


if __name__ == "__main__":
    main()
