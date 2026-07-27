"""Tabla conciliacion_banco_extracto (Banco/Fecha/Referencia/Monto) persistente.

Revision ID: 081_conciliacion_banco_extracto
Revises: 080_concesionarios_catalogo
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "081_conciliacion_banco_extracto"
down_revision = "080_concesionarios_catalogo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "conciliacion_banco_extracto" not in tables:
        op.create_table(
            "conciliacion_banco_extracto",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("banco", sa.String(length=40), nullable=False),
            sa.Column("fecha", sa.Date(), nullable=True),
            sa.Column("referencia", sa.Text(), nullable=False),
            sa.Column("referencia_norm", sa.Text(), nullable=True),
            sa.Column("monto", sa.Numeric(14, 2), nullable=True),
            sa.Column(
                "moneda",
                sa.String(length=3),
                nullable=False,
                server_default=sa.text("'USD'"),
            ),
            sa.Column("clave_natural", sa.Text(), nullable=False),
            sa.Column("lote_origen_id", sa.Integer(), nullable=True),
            sa.Column("archivo_nombre", sa.String(length=255), nullable=True),
            sa.Column(
                "creado_en",
                sa.DateTime(timezone=False),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "actualizado_en",
                sa.DateTime(timezone=False),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["lote_origen_id"],
                ["conciliacion_banco_ocr_lote.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_conciliacion_banco_extracto_clave "
        "ON conciliacion_banco_extracto (clave_natural)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_extracto_banco "
        "ON conciliacion_banco_extracto (banco)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_extracto_fecha "
        "ON conciliacion_banco_extracto (fecha)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_extracto_referencia_norm "
        "ON conciliacion_banco_extracto (referencia_norm)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conciliacion_banco_extracto_lote_origen "
        "ON conciliacion_banco_extracto (lote_origen_id)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "conciliacion_banco_extracto" in set(inspector.get_table_names()):
        op.drop_table("conciliacion_banco_extracto")
