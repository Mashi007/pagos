"""Add finiquitador role to usuarios table

Revision ID: 038_add_rol_finiquitador
Revises: 037_add_payload_snapshot_auditoria
Create Date: 2026-03-30 10:00:00.000000

Adds support for finiquitador role: users with access only to finiquito gestion page.
Allows granular access control for finiquito workflow users.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '038_add_rol_finiquitador'
down_revision = '037_add_payload_snapshot_auditoria'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update the CHECK constraint on rol column to include 'finiquitador'
    # For PostgreSQL: drop and recreate the constraint
    op.execute("""
        ALTER TABLE usuarios 
        DROP CONSTRAINT IF EXISTS usuarios_rol_check
    """)
    
    op.execute("""
        ALTER TABLE usuarios 
        ADD CONSTRAINT usuarios_rol_check 
        CHECK (rol IN ('administrador', 'operativo', 'finiquitador'))
    """)
    
    # Add comment for documentation
    op.execute("""
        COMMENT ON COLUMN usuarios.rol IS 
        'User role: administrador (full access), operativo (limited access), finiquitador (finiquito gestion only)'
    """)


def downgrade() -> None:
    # Restore original constraint without finiquitador
    op.execute("""
        ALTER TABLE usuarios 
        DROP CONSTRAINT IF EXISTS usuarios_rol_check
    """)
    
    op.execute("""
        ALTER TABLE usuarios 
        ADD CONSTRAINT usuarios_rol_check 
        CHECK (rol IN ('administrador', 'operativo'))
    """)
