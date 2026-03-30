"""auditoria_cartera_revision.payload_snapshot JSONB (snapshot al aceptar excepcion).

Revision ID: 032_auditoria_cartera_revision_payload_snapshot
Revises: 031_pagos_reportados_canal_ingreso
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "032_auditoria_cartera_revision_payload_snapshot"
down_revision = "031_pagos_reportados_canal_ingreso"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auditoria_cartera_revision",
        sa.Column(
            "payload_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("auditoria_cartera_revision", "payload_snapshot")
