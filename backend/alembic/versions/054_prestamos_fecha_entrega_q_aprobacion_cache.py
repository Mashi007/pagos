"""prestamos: caché comparación columna Q (hoja) vs fecha_aprobación (sistema).

Revision ID: 054_prestamos_fecha_entrega_q_aprobacion_cache
Revises: 053_prestamos_abonos_drive_cuotas_cache
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "054_prestamos_fecha_entrega_q_aprobacion_cache"
down_revision = "053_prestamos_abonos_drive_cuotas_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "prestamos" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("prestamos")}
    if "fecha_entrega_q_aprobacion_cache" not in cols:
        op.add_column(
            "prestamos",
            sa.Column("fecha_entrega_q_aprobacion_cache", sa.JSON(), nullable=True),
        )
        insp = inspect(bind)
        cols = {c["name"] for c in insp.get_columns("prestamos")}
    if "fecha_entrega_q_aprobacion_cache_at" not in cols:
        op.add_column(
            "prestamos",
            sa.Column(
                "fecha_entrega_q_aprobacion_cache_at",
                sa.DateTime(timezone=False),
                nullable=True,
            ),
        )


def downgrade() -> None:
    op.drop_column("prestamos", "fecha_entrega_q_aprobacion_cache_at")
    op.drop_column("prestamos", "fecha_entrega_q_aprobacion_cache")
