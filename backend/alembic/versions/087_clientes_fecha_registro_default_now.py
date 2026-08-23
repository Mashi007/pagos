"""Asegura DEFAULT CURRENT_TIMESTAMP en clientes.fecha_registro.

Revision ID: 087_clientes_fecha_registro_default_now
Revises: 086_evidencias_pdf_motor
Create Date: 2026-08-23

Evita que altas nuevas (manual/Drive/Excel) hereden el literal antiguo
'2025-10-31 00:00:00' si la migración 006 no aplicó bien en Postgres.
"""
from alembic import op


revision = "087_clientes_fecha_registro_default_now"
down_revision = "086_evidencias_pdf_motor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE clientes
          ALTER COLUMN fecha_registro SET DEFAULT CURRENT_TIMESTAMP
        """
    )


def downgrade() -> None:
    # No restaurar el literal 2025-10-31 (era un bug).
    op.execute(
        """
        ALTER TABLE clientes
          ALTER COLUMN fecha_registro SET DEFAULT CURRENT_TIMESTAMP
        """
    )
