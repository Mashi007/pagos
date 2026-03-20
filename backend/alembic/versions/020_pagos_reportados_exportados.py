"""create pagos_reportados_exportados table

Revision ID: 020_pagos_reportados_exportados
Revises: 019_prestamos_estado_liquidado
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '020_pagos_reportados_exportados'
down_revision = '019_prestamos_estado_liquidado'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pagos_reportados_exportados',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pago_reportado_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['pago_reportado_id'], ['pagos_reportados.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pago_reportado_id'),
    )
    op.create_index('ix_pagos_reportados_exportados_id', 'pagos_reportados_exportados', ['id'], unique=False)
    op.create_index(
        'ix_pagos_reportados_exportados_pago_reportado_id',
        'pagos_reportados_exportados',
        ['pago_reportado_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_pagos_reportados_exportados_pago_reportado_id', table_name='pagos_reportados_exportados')
    op.drop_index('ix_pagos_reportados_exportados_id', table_name='pagos_reportados_exportados')
    op.drop_table('pagos_reportados_exportados')
