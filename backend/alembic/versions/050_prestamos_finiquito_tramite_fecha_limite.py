"""prestamos: finiquito_tramite_fecha_limite (plazo 15 dias laborales en EN_PROCESO).

Revision ID: 050_prestamos_finiquito_tramite_fecha_limite
Revises: 049_prestamos_estado_gestion_finiquito
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "050_prestamos_finiquito_tramite_fecha_limite"
down_revision = "049_prestamos_estado_gestion_finiquito"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("prestamos")}
    if "finiquito_tramite_fecha_limite" in cols:
        return
    op.add_column(
        "prestamos",
        sa.Column("finiquito_tramite_fecha_limite", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("prestamos")}
    if "finiquito_tramite_fecha_limite" not in cols:
        return
    op.drop_column("prestamos", "finiquito_tramite_fecha_limite")
