"""Tabla finiquito_conciliacion_reserva (comprobantes temporales flujo Visto).

Revision ID: 072_finiquito_conciliacion_reserva
Revises: 071_conciliacion_sheet_scan_coverage
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "072_finiquito_conciliacion_reserva"
down_revision = "071_conciliacion_sheet_scan_coverage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if insp.has_table("finiquito_conciliacion_reserva"):
        return
    op.create_table(
        "finiquito_conciliacion_reserva",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("caso_id", sa.Integer(), nullable=False),
        sa.Column("prestamo_id", sa.Integer(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pago_id_origen", sa.Integer(), nullable=True),
        sa.Column("cedula_cliente", sa.String(length=20), nullable=True),
        sa.Column("monto_pagado", sa.Numeric(14, 2), nullable=False),
        sa.Column("fecha_pago", sa.DateTime(), nullable=False),
        sa.Column("numero_documento", sa.String(length=100), nullable=True),
        sa.Column("referencia_pago", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("institucion_bancaria", sa.String(length=255), nullable=True),
        sa.Column("link_comprobante", sa.Text(), nullable=True),
        sa.Column("documento_ruta", sa.String(length=255), nullable=True),
        sa.Column("moneda_registro", sa.String(length=10), nullable=True),
        sa.Column("monto_bs_original", sa.Numeric(15, 2), nullable=True),
        sa.Column("tasa_cambio_bs_usd", sa.Numeric(15, 6), nullable=True),
        sa.Column("conciliado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("pago_id_recriado", sa.Integer(), nullable=True),
        sa.Column("ocr_ok", sa.Boolean(), nullable=True),
        sa.Column("ocr_error", sa.Text(), nullable=True),
        sa.Column("ocr_sugerencia_json", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["caso_id"], ["finiquito_casos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prestamo_id"], ["prestamos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finiquito_conciliacion_reserva_caso_id",
        "finiquito_conciliacion_reserva",
        ["caso_id"],
    )
    op.create_index(
        "ix_finiquito_conciliacion_reserva_prestamo_id",
        "finiquito_conciliacion_reserva",
        ["prestamo_id"],
    )
    op.create_index(
        "ix_finiquito_conc_reserva_caso_orden",
        "finiquito_conciliacion_reserva",
        ["caso_id", "orden"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("finiquito_conciliacion_reserva"):
        return
    op.drop_index("ix_finiquito_conc_reserva_caso_orden", table_name="finiquito_conciliacion_reserva")
    op.drop_index(
        "ix_finiquito_conciliacion_reserva_prestamo_id",
        table_name="finiquito_conciliacion_reserva",
    )
    op.drop_index(
        "ix_finiquito_conciliacion_reserva_caso_id",
        table_name="finiquito_conciliacion_reserva",
    )
    op.drop_table("finiquito_conciliacion_reserva")
