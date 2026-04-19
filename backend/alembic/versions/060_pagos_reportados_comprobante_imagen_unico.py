"""Comprobante reportado: FK a pago_comprobante_imagen; elimina columnas binarias duplicadas.

Revision ID: 060_pagos_reportados_comprobante_imagen_unico
Revises: 059_pagos_gmail_abcd_cuotas_traza
Create Date: 2026-04-19
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "060_pagos_reportados_comprobante_imagen_unico"
down_revision = "059_pagos_gmail_abcd_cuotas_traza"
branch_labels = None
depends_on = None

_MIME_PERMITIDOS = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/heic",
        "application/pdf",
    }
)


def _normalizar_mime(raw: str | None) -> str:
    s = (raw or "").split(";")[0].strip().lower()
    if s == "image/jpg":
        s = "image/jpeg"
    if s in _MIME_PERMITIDOS:
        return s
    return "application/octet-stream"


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

    # Migrar binarios legacy a pago_comprobante_imagen
    if "comprobante" in cols:
        rows = bind.execute(
            text(
                "SELECT id, comprobante, comprobante_tipo FROM pagos_reportados "
                "WHERE comprobante IS NOT NULL AND (comprobante_imagen_id IS NULL OR comprobante_imagen_id = '')"
            )
        ).fetchall()
        for rid, blob, ctype in rows:
            if not blob:
                continue
            uid = uuid.uuid4().hex
            ct = _normalizar_mime(str(ctype) if ctype is not None else "")
            bind.execute(
                text(
                    "INSERT INTO pago_comprobante_imagen (id, content_type, imagen_data) "
                    "VALUES (:id, :ct, :data)"
                ),
                {"id": uid, "ct": ct, "data": blob},
            )
            bind.execute(
                text("UPDATE pagos_reportados SET comprobante_imagen_id = :uid WHERE id = :rid"),
                {"uid": uid, "rid": rid},
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
