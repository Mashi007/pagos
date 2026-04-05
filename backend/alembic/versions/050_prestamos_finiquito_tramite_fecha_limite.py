"""prestamos: finiquito_tramite_fecha_limite (plazo 15 dias laborales en EN_PROCESO).

Revision ID: 050_prestamos_finiquito_tramite_fecha_limite
Revises: 049_prestamos_estado_gestion_finiquito
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "050_prestamos_finiquito_tramite_fecha_limite"
down_revision = "049_prestamos_estado_gestion_finiquito"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prestamos",
        sa.Column("finiquito_tramite_fecha_limite", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prestamos", "finiquito_tramite_fecha_limite")
