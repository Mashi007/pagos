"""Add cedula column to usuarios table

Revision ID: 040_add_cedula_to_usuarios
Revises: 039_remove_rol_finiquitador
Create Date: 2026-04-01 01:00:00.000000

Adds cedula (identity document) as a unique, required field for all users.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '040_add_cedula_to_usuarios'
down_revision = '039_remove_rol_finiquitador'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cedula column as nullable first
    op.add_column('usuarios', sa.Column('cedula', sa.String(50), nullable=True))
    
    # Create index for cedula
    op.create_index('ix_usuarios_cedula', 'usuarios', ['cedula'], unique=True)
    
    # For existing users, set cedula to email (temporary, should be updated manually)
    op.execute("""
        UPDATE usuarios SET cedula = email WHERE cedula IS NULL
    """)
    
    # Now make cedula NOT NULL
    op.alter_column('usuarios', 'cedula', nullable=False)
    
    # Add comment for documentation
    op.execute("""
        COMMENT ON COLUMN usuarios.cedula IS 
        'Unique identity document number (cédula) - required and unique'
    """)


def downgrade() -> None:
    # Drop index and column
    op.drop_index('ix_usuarios_cedula', 'usuarios')
    op.drop_column('usuarios', 'cedula')
