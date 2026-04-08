"""Fix Cliente fecha_registro default from hardcoded date to CURRENT_TIMESTAMP.

Revision ID: 006_fix_cliente_fecha_registro_default
Revises: 005_add_cuotas_columns
Create Date: 2026-03-06 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "006_fix_cliente_fecha_registro_default"
down_revision = "005_add_cuotas_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old default that had a hardcoded date ('2025-10-31 00:00:00')
    # and set it to CURRENT_TIMESTAMP
    with op.batch_operations.BatchOperations() as batch_op:
        batch_op.alter_column(
            'clientes',
            'fecha_registro',
            existing_type=sa.DateTime(timezone=False),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            existing_server_default=sa.text("'2025-10-31 00:00:00'"),
            nullable=False
        )


def downgrade() -> None:
    # Revert back to the old hardcoded default (for rollback purposes)
    with op.batch_operations.BatchOperations() as batch_op:
        batch_op.alter_column(
            'clientes',
            'fecha_registro',
            existing_type=sa.DateTime(timezone=False),
            server_default=sa.text("'2025-10-31 00:00:00'"),
            existing_server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        )
