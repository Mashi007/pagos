"""Tabla cobros_publico_codigos OTP reporte de pago publico

Revision ID: 042_cobros_publico_codigos
Revises: 041_merge_nombre_apellido
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "042_cobros_publico_codigos"
down_revision = "041_merge_nombre_apellido"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("cobros_publico_codigos"):
        op.create_table(
            "cobros_publico_codigos",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("cedula_normalizada", sa.String(20), nullable=False),
            sa.Column("email", sa.String(100), nullable=False),
            sa.Column("codigo", sa.String(10), nullable=False),
            sa.Column("expira_en", sa.DateTime(timezone=False), nullable=False),
            sa.Column("usado", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("creado_en", sa.DateTime(timezone=False), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_cobros_publico_codigos_cedula_normalizada",
            "cobros_publico_codigos",
            ["cedula_normalizada"],
            unique=False,
        )
    else:
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_cobros_publico_codigos_cedula_normalizada "
            "ON cobros_publico_codigos (cedula_normalizada);"
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("cobros_publico_codigos"):
        return
    op.drop_index(
        "ix_cobros_publico_codigos_cedula_normalizada",
        table_name="cobros_publico_codigos",
    )
    op.drop_table("cobros_publico_codigos")
