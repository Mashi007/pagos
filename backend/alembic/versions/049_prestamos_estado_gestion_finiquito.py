"""prestamos: columna estado_gestion_finiquito (ANTIGUO, EN_PROCESO, TERMINADO).

Revision ID: 049_prestamos_estado_gestion_finiquito
Revises: 048_retraso_mv_refresh_trigger
Create Date: 2026-04-05

Refleja en el préstamo la fase finiquito para consulta de cualquier usuario.
Backfill desde finiquito_casos existentes.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "049_prestamos_estado_gestion_finiquito"
down_revision = "048_retraso_mv_refresh_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("prestamos")}
    if "estado_gestion_finiquito" not in cols:
        op.add_column(
            "prestamos",
            sa.Column(
                "estado_gestion_finiquito",
                sa.String(length=32),
                nullable=True,
            ),
        )
    insp = inspect(bind)
    idx_names = {i["name"] for i in insp.get_indexes("prestamos")}
    if "ix_prestamos_estado_gestion_finiquito" not in idx_names:
        op.create_index(
            "ix_prestamos_estado_gestion_finiquito",
            "prestamos",
            ["estado_gestion_finiquito"],
            unique=False,
        )
    op.execute(
        """
        UPDATE prestamos p
        SET estado_gestion_finiquito = c.estado
        FROM finiquito_casos c
        WHERE c.prestamo_id = p.id
          AND UPPER(TRIM(c.estado)) IN ('ANTIGUO', 'EN_PROCESO', 'TERMINADO');
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    idx_names = {i["name"] for i in insp.get_indexes("prestamos")}
    if "ix_prestamos_estado_gestion_finiquito" in idx_names:
        op.drop_index("ix_prestamos_estado_gestion_finiquito", table_name="prestamos")
    cols = {c["name"] for c in insp.get_columns("prestamos")}
    if "estado_gestion_finiquito" in cols:
        op.drop_column("prestamos", "estado_gestion_finiquito")
