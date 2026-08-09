"""Columna pdf_motor en evidencias_notificacion.

Revision ID: 086_evidencias_pdf_motor
Revises: 085_aseguradora_universo
Create Date: 2026-08-09
"""

from alembic import op
import sqlalchemy as sa


revision = "086_evidencias_pdf_motor"
down_revision = "085_aseguradora_universo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("evidencias_notificacion"):
        return
    cols = {c["name"] for c in insp.get_columns("evidencias_notificacion")}
    if "pdf_motor" not in cols:
        op.add_column(
            "evidencias_notificacion",
            sa.Column("pdf_motor", sa.String(length=20), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("evidencias_notificacion"):
        return
    cols = {c["name"] for c in insp.get_columns("evidencias_notificacion")}
    if "pdf_motor" in cols:
        op.drop_column("evidencias_notificacion", "pdf_motor")
