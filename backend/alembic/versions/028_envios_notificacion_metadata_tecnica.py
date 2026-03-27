"""envios_notificacion: columna metadata_tecnica (JSON); fusion de heads Alembic

Revision ID: 028_envios_notificacion_metadata_tecnica
Revises: 027_envios_notificacion_snapshot, 027_conversaciones_ai
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "028_envios_notificacion_metadata_tecnica"
down_revision = ("027_envios_notificacion_snapshot", "027_conversaciones_ai")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "envios_notificacion",
        sa.Column("metadata_tecnica", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("envios_notificacion", "metadata_tecnica")
