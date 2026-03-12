"""Añadir asunto e índice cedula en envios_notificacion (historial por cédula)

Revision ID: 013_envios_notificacion_asunto
Revises: 012_envios_notificacion
Create Date: 2026-03

"""
from alembic import op
import sqlalchemy as sa


revision = "013_envios_notificacion_asunto"
down_revision = "012_envios_notificacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("envios_notificacion", sa.Column("asunto", sa.String(500), nullable=True))
    op.create_index("ix_envios_notificacion_cedula", "envios_notificacion", ["cedula"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_envios_notificacion_cedula", table_name="envios_notificacion")
    op.drop_column("envios_notificacion", "asunto")
