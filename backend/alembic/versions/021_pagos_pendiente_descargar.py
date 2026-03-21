"""create pagos_pendiente_descargar table

Revision ID: 021_pagos_pendiente_descargar
Revises: 020_pagos_reportados_exportados
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021_pagos_pendiente_descargar'
down_revision = '020_pagos_reportados_exportados'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pagos_pendiente_descargar',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pago_reportado_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['pago_reportado_id'], ['pagos_reportados.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pagos_pendiente_descargar_id', 'pagos_pendiente_descargar', ['id'], unique=False)
    op.create_index(
        'ix_pagos_pendiente_descargar_pago_reportado_id',
        'pagos_pendiente_descargar',
        ['pago_reportado_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_pagos_pendiente_descargar_pago_reportado_id', table_name='pagos_pendiente_descargar')
    op.drop_index('ix_pagos_pendiente_descargar_id', table_name='pagos_pendiente_descargar')
    op.drop_table('pagos_pendiente_descargar')
