"""Remove finiquitador role and standardize to RBAC

Revision ID: 039_remove_rol_finiquitador
Revises: 038_add_rol_finiquitador
Create Date: 2026-04-01 00:00:00.000000

Removes finiquitador role and migrates to standardized RBAC roles:
  - admin (full access)
  - manager (operational management)
  - operator (basic operations)
  - viewer (read-only)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '039_remove_rol_finiquitador'
down_revision = '038_add_rol_finiquitador'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update users: finiquitador and administrador -> admin
    op.execute("""
        UPDATE usuarios SET rol = 'admin' WHERE rol IN ('finiquitador', 'administrador')
    """)
    
    # Update operativo -> viewer (read-only is default for non-admin)
    op.execute("""
        UPDATE usuarios SET rol = 'viewer' WHERE rol = 'operativo'
    """)
    
    # Update the CHECK constraint on rol column for RBAC roles
    op.execute("""
        ALTER TABLE usuarios 
        DROP CONSTRAINT IF EXISTS usuarios_rol_check
    """)
    
    op.execute("""
        ALTER TABLE usuarios 
        ADD CONSTRAINT usuarios_rol_check 
        CHECK (rol IN ('admin', 'manager', 'operator', 'viewer'))
    """)
    
    # Update comment for documentation
    op.execute("""
        COMMENT ON COLUMN usuarios.rol IS 
        'User role (RBAC standard): admin (full), manager (operational), operator (basic), viewer (read-only)'
    """)


def downgrade() -> None:
    # Restore to previous state
    op.execute("""
        UPDATE usuarios SET rol = 'administrador' WHERE rol = 'admin'
    """)
    
    op.execute("""
        UPDATE usuarios SET rol = 'operativo' WHERE rol = 'viewer'
    """)
    
    op.execute("""
        ALTER TABLE usuarios 
        DROP CONSTRAINT IF EXISTS usuarios_rol_check
    """)
    
    op.execute("""
        ALTER TABLE usuarios 
        ADD CONSTRAINT usuarios_rol_check 
        CHECK (rol IN ('administrador', 'operativo', 'finiquitador'))
    """)


