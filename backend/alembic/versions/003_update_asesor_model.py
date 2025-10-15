"""Update asesor model - make apellido and email nullable

Revision ID: 003_update_asesor_model
Revises: 002_add_cliente_foreignkeys
Create Date: 2025-10-15 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_update_asesor_model'
down_revision = '002_add_cliente_foreignkeys'
branch_labels = None
depends_on = None


def upgrade():
    """Update asesor model to make apellido and email nullable"""
    # Make apellido nullable
    op.alter_column('asesores', 'apellido',
                    existing_type=sa.VARCHAR(255),
                    nullable=True)
    
    # Make email nullable
    op.alter_column('asesores', 'email',
                    existing_type=sa.VARCHAR(255),
                    nullable=True)


def downgrade():
    """Revert asesor model changes"""
    # Make apellido not nullable
    op.alter_column('asesores', 'apellido',
                    existing_type=sa.VARCHAR(255),
                    nullable=False)
    
    # Make email not nullable
    op.alter_column('asesores', 'email',
                    existing_type=sa.VARCHAR(255),
                    nullable=False)
