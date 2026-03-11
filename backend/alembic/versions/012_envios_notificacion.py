"""Tabla envios_notificacion para estadísticas y rebotados por pestaña

Revision ID: 012_envios_notificacion
Revises: 011_estado_cuenta_codigos
Create Date: 2026-03

"""
from alembic import op
import sqlalchemy as sa


revision = "012_envios_notificacion"
down_revision = "011_estado_cuenta_codigos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "envios_notificacion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fecha_envio", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column("tipo_tab", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=True),
        sa.Column("cedula", sa.String(50), nullable=True),
        sa.Column("exito", sa.Boolean(), nullable=False),
        sa.Column("error_mensaje", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_envios_notificacion_id", "envios_notificacion", ["id"], unique=False)
    op.create_index("ix_envios_notificacion_tipo_tab", "envios_notificacion", ["tipo_tab"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_envios_notificacion_tipo_tab", table_name="envios_notificacion")
    op.drop_index("ix_envios_notificacion_id", table_name="envios_notificacion")
    op.drop_table("envios_notificacion")
