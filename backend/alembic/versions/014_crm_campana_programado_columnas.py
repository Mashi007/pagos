"""Añadir columnas de programación a crm_campana (programado_cada_dias, programado_cada_horas, programado_proxima_ejecucion)

Revision ID: 014_crm_campana_programado
Revises: 013_envios_notificacion_asunto
Create Date: 2026-03

"""
from alembic import op
import sqlalchemy as sa


revision = "014_crm_campana_programado"
down_revision = "013_envios_notificacion_asunto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crm_campana", sa.Column("programado_cada_dias", sa.Integer(), nullable=True))
    op.add_column("crm_campana", sa.Column("programado_cada_horas", sa.Integer(), nullable=True))
    op.add_column("crm_campana", sa.Column("programado_proxima_ejecucion", sa.DateTime(timezone=False), nullable=True))


def downgrade() -> None:
    op.drop_column("crm_campana", "programado_proxima_ejecucion")
    op.drop_column("crm_campana", "programado_cada_horas")
    op.drop_column("crm_campana", "programado_cada_dias")
