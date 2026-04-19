"""Tabla recibos_email_envio: idempotencia envíos Recibos (cedula + día + slot).

Revision ID: 062_recibos_email_envio
Revises: 061_pagos_whatsapp_comprobante_imagen_id
Create Date: 2026-04-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "062_recibos_email_envio"
down_revision = "061_pagos_whatsapp_comprobante_imagen_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "recibos_email_envio" in insp.get_table_names():
        return
    op.create_table(
        "recibos_email_envio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cedula_normalizada", sa.String(length=32), nullable=False),
        sa.Column("fecha_dia", sa.Date(), nullable=False),
        sa.Column("slot", sa.String(length=16), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cedula_normalizada",
            "fecha_dia",
            "slot",
            name="uq_recibos_email_envio_cedula_dia_slot",
        ),
    )
    op.create_index(
        "ix_recibos_email_envio_cedula_normalizada",
        "recibos_email_envio",
        ["cedula_normalizada"],
        unique=False,
    )
    op.create_index(
        "ix_recibos_email_envio_fecha_dia",
        "recibos_email_envio",
        ["fecha_dia"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "recibos_email_envio" not in insp.get_table_names():
        return
    op.drop_index("ix_recibos_email_envio_fecha_dia", table_name="recibos_email_envio")
    op.drop_index("ix_recibos_email_envio_cedula_normalizada", table_name="recibos_email_envio")
    op.drop_table("recibos_email_envio")
