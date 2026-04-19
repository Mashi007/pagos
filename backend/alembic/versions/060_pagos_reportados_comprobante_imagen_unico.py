"""Comprobante reportado: FK a pago_comprobante_imagen; elimina columnas binarias duplicadas.

Revision ID: 060_pagos_reportados_comprobante_imagen_unico
Revises: 059_pagos_gmail_abcd_cuotas_traza
Create Date: 2026-04-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "060_pagos_reportados_comprobante_imagen_unico"
down_revision = "059_pagos_gmail_abcd_cuotas_traza"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    # Tabla canónica del binario (Gmail, Infopagos/cobros público, alta manual).
    # Debe existir antes de migrar bytea desde `pagos_reportados` o de crear la FK.
    if "pago_comprobante_imagen" not in insp.get_table_names():
        op.create_table(
            "pago_comprobante_imagen",
            sa.Column("id", sa.String(length=32), nullable=False),
            sa.Column("content_type", sa.String(length=80), nullable=False),
            sa.Column("imagen_data", sa.LargeBinary(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id", name="pago_comprobante_imagen_pkey"),
        )
        insp = inspect(bind)

    if "pagos_reportados" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("pagos_reportados")}

    if "comprobante_imagen_id" not in cols:
        op.add_column(
            "pagos_reportados",
            sa.Column("comprobante_imagen_id", sa.String(length=32), nullable=True),
        )

    # Migrar binarios legacy a pago_comprobante_imagen (SQL por lotes: evita N round-trips).
    if "comprobante" in cols:
        bind.execute(
            text(
                """
                CREATE TEMP TABLE _060_migrate_pr_img (
                    pr_id integer NOT NULL,
                    new_id varchar(32) NOT NULL,
                    content_type varchar(80) NOT NULL,
                    imagen_data bytea NOT NULL
                ) ON COMMIT DROP
                """
            )
        )
        bind.execute(
            text(
                """
                INSERT INTO _060_migrate_pr_img (pr_id, new_id, content_type, imagen_data)
                SELECT
                    pr.id,
                    md5(random()::text || clock_timestamp()::text || pr.id::text),
                    CASE
                        WHEN lower(trim(split_part(COALESCE(pr.comprobante_tipo, ''), ';', 1)))
                            = 'image/jpg' THEN 'image/jpeg'
                        WHEN lower(trim(split_part(COALESCE(pr.comprobante_tipo, ''), ';', 1))) IN (
                            'image/jpeg', 'image/png', 'image/webp', 'image/gif',
                            'image/heic', 'application/pdf'
                        ) THEN lower(trim(split_part(COALESCE(pr.comprobante_tipo, ''), ';', 1)))
                        ELSE 'application/octet-stream'
                    END,
                    pr.comprobante
                FROM pagos_reportados pr
                WHERE pr.comprobante IS NOT NULL
                  AND (pr.comprobante_imagen_id IS NULL OR pr.comprobante_imagen_id = '')
                """
            )
        )
        bind.execute(
            text(
                """
                INSERT INTO pago_comprobante_imagen (id, content_type, imagen_data)
                SELECT new_id, content_type, imagen_data FROM _060_migrate_pr_img
                """
            )
        )
        bind.execute(
            text(
                """
                UPDATE pagos_reportados pr
                SET comprobante_imagen_id = m.new_id
                FROM _060_migrate_pr_img m
                WHERE pr.id = m.pr_id
                """
            )
        )

    insp = inspect(bind)
    fk_names = {fk["name"] for fk in insp.get_foreign_keys("pagos_reportados")}
    if "fk_pagos_reportados_comprobante_imagen_id" not in fk_names:
        op.create_foreign_key(
            "fk_pagos_reportados_comprobante_imagen_id",
            "pagos_reportados",
            "pago_comprobante_imagen",
            ["comprobante_imagen_id"],
            ["id"],
            ondelete="SET NULL",
        )

    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("pagos_reportados")}
    if "comprobante_tipo" in cols:
        op.drop_column("pagos_reportados", "comprobante_tipo")
    if "comprobante" in cols:
        op.drop_column("pagos_reportados", "comprobante")

    insp = inspect(bind)
    idx_names = {i["name"] for i in insp.get_indexes("pagos_reportados")}
    if "ix_pagos_reportados_comprobante_imagen_id" not in idx_names:
        op.create_index(
            "ix_pagos_reportados_comprobante_imagen_id",
            "pagos_reportados",
            ["comprobante_imagen_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_reportados" not in insp.get_table_names():
        return
    try:
        op.drop_index("ix_pagos_reportados_comprobante_imagen_id", table_name="pagos_reportados")
    except Exception:
        pass
    try:
        op.drop_constraint(
            "fk_pagos_reportados_comprobante_imagen_id",
            "pagos_reportados",
            type_="foreignkey",
        )
    except Exception:
        pass
    cols = {c["name"] for c in insp.get_columns("pagos_reportados")}
    if "comprobante" not in cols:
        op.add_column(
            "pagos_reportados",
            sa.Column("comprobante", sa.LargeBinary(), nullable=True),
        )
    if "comprobante_tipo" not in cols:
        op.add_column(
            "pagos_reportados",
            sa.Column("comprobante_tipo", sa.String(length=100), nullable=True),
        )
    if "comprobante_imagen_id" in cols:
        op.drop_column("pagos_reportados", "comprobante_imagen_id")
