"""WhatsApp informe: comprobante binario vía pago_comprobante_imagen (FK); imagen bytea opcional.

Revision ID: 061_pagos_whatsapp_comprobante_imagen_id
Revises: 060_pagos_reportados_comprobante_imagen_unico
Create Date: 2026-04-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "061_pagos_whatsapp_comprobante_imagen_id"
down_revision = "060_pagos_reportados_comprobante_imagen_unico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_whatsapp" not in insp.get_table_names():
        return
    if "pago_comprobante_imagen" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("pagos_whatsapp")}
    if "comprobante_imagen_id" not in cols:
        op.add_column(
            "pagos_whatsapp",
            sa.Column("comprobante_imagen_id", sa.String(length=32), nullable=True),
        )
        insp = inspect(bind)

    fk_names = {fk["name"] for fk in insp.get_foreign_keys("pagos_whatsapp")}
    if "fk_pagos_whatsapp_comprobante_imagen_id" not in fk_names:
        op.create_foreign_key(
            "fk_pagos_whatsapp_comprobante_imagen_id",
            "pagos_whatsapp",
            "pago_comprobante_imagen",
            ["comprobante_imagen_id"],
            ["id"],
            ondelete="SET NULL",
        )

    insp = inspect(bind)
    idx_names = {i["name"] for i in insp.get_indexes("pagos_whatsapp")}
    if "ix_pagos_whatsapp_comprobante_imagen_id" not in idx_names:
        op.create_index(
            "ix_pagos_whatsapp_comprobante_imagen_id",
            "pagos_whatsapp",
            ["comprobante_imagen_id"],
            unique=False,
        )

    # Dejar de exigir duplicado bytea en esta tabla (nuevas filas: solo FK).
    op.alter_column(
        "pagos_whatsapp",
        "imagen",
        existing_type=sa.LargeBinary(),
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_whatsapp" not in insp.get_table_names():
        return
    try:
        op.drop_index("ix_pagos_whatsapp_comprobante_imagen_id", table_name="pagos_whatsapp")
    except Exception:
        pass
    try:
        op.drop_constraint(
            "fk_pagos_whatsapp_comprobante_imagen_id",
            "pagos_whatsapp",
            type_="foreignkey",
        )
    except Exception:
        pass
    cols = {c["name"] for c in insp.get_columns("pagos_whatsapp")}
    if "comprobante_imagen_id" in cols:
        op.drop_column("pagos_whatsapp", "comprobante_imagen_id")
    try:
        op.alter_column(
            "pagos_whatsapp",
            "imagen",
            existing_type=sa.LargeBinary(),
            nullable=False,
        )
    except Exception:
        pass
