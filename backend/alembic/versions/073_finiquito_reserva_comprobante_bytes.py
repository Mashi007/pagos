"""Bytes de comprobante en reserva Visto (re-OCR solo desde lo guardado).

Revision ID: 073_finiquito_reserva_comprobante_bytes
Revises: 072_finiquito_conciliacion_reserva
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "073_finiquito_reserva_comprobante_bytes"
down_revision = "072_finiquito_conciliacion_reserva"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("finiquito_conciliacion_reserva"):
        return
    cols = {c["name"] for c in insp.get_columns("finiquito_conciliacion_reserva")}
    if "comprobante_imagen_data" not in cols:
        op.add_column(
            "finiquito_conciliacion_reserva",
            sa.Column("comprobante_imagen_data", sa.LargeBinary(), nullable=True),
        )
    if "comprobante_content_type" not in cols:
        op.add_column(
            "finiquito_conciliacion_reserva",
            sa.Column("comprobante_content_type", sa.String(length=80), nullable=True),
        )
    if "comprobante_nombre_archivo" not in cols:
        op.add_column(
            "finiquito_conciliacion_reserva",
            sa.Column("comprobante_nombre_archivo", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("finiquito_conciliacion_reserva"):
        return
    cols = {c["name"] for c in insp.get_columns("finiquito_conciliacion_reserva")}
    if "comprobante_nombre_archivo" in cols:
        op.drop_column("finiquito_conciliacion_reserva", "comprobante_nombre_archivo")
    if "comprobante_content_type" in cols:
        op.drop_column("finiquito_conciliacion_reserva", "comprobante_content_type")
    if "comprobante_imagen_data" in cols:
        op.drop_column("finiquito_conciliacion_reserva", "comprobante_imagen_data")
