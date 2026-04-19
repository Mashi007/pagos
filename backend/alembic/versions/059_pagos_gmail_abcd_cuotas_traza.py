"""Tabla trazabilidad Gmail ABCD → pagos → cuotas.

Revision ID: 059_pagos_gmail_abcd_cuotas_traza
Revises: 058_clientes_drive_export_excel_auditoria
Create Date: 2026-04-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "059_pagos_gmail_abcd_cuotas_traza"
down_revision = "058_clientes_drive_export_excel_auditoria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_gmail_abcd_cuotas_traza" in insp.get_table_names():
        return
    op.create_table(
        "pagos_gmail_abcd_cuotas_traza",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sync_id", sa.Integer(), nullable=True),
        sa.Column("sync_item_id", sa.Integer(), nullable=True),
        sa.Column("plantilla_fmt", sa.String(length=1), nullable=False),
        sa.Column("cedula", sa.String(length=50), nullable=True),
        sa.Column("numero_referencia", sa.String(length=200), nullable=True),
        sa.Column("banco_excel", sa.String(length=50), nullable=True),
        sa.Column("archivo_adjunto", sa.String(length=500), nullable=True),
        sa.Column("comprobante_imagen_id", sa.String(length=32), nullable=True),
        sa.Column(
            "duplicado_documento",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("etapa_final", sa.String(length=40), nullable=False),
        sa.Column("motivo", sa.String(length=80), nullable=True),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("pago_id", sa.Integer(), nullable=True),
        sa.Column("prestamo_id", sa.Integer(), nullable=True),
        sa.Column(
            "cuotas_completadas",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "cuotas_parciales",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("conciliado_final", sa.Boolean(), nullable=True),
        sa.Column("pago_estado_final", sa.String(length=30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["sync_id"], ["pagos_gmail_sync.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["sync_item_id"],
            ["pagos_gmail_sync_item.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["pago_id"], ["pagos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prestamo_id"], ["prestamos.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_pagos_gmail_abcd_traza_sync_item",
        "pagos_gmail_abcd_cuotas_traza",
        ["sync_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_pagos_gmail_abcd_traza_sync",
        "pagos_gmail_abcd_cuotas_traza",
        ["sync_id"],
        unique=False,
    )
    op.create_index(
        "ix_pagos_gmail_abcd_traza_etapa",
        "pagos_gmail_abcd_cuotas_traza",
        ["etapa_final"],
        unique=False,
    )
    op.create_index(
        "ix_pagos_gmail_abcd_traza_created",
        "pagos_gmail_abcd_cuotas_traza",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_pagos_gmail_abcd_traza_pago",
        "pagos_gmail_abcd_cuotas_traza",
        ["pago_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "pagos_gmail_abcd_cuotas_traza" not in insp.get_table_names():
        return
    for name in (
        "ix_pagos_gmail_abcd_traza_pago",
        "ix_pagos_gmail_abcd_traza_created",
        "ix_pagos_gmail_abcd_traza_etapa",
        "ix_pagos_gmail_abcd_traza_sync",
        "ix_pagos_gmail_abcd_traza_sync_item",
    ):
        try:
            op.drop_index(name, table_name="pagos_gmail_abcd_cuotas_traza")
        except Exception:
            pass
    op.drop_table("pagos_gmail_abcd_cuotas_traza")
