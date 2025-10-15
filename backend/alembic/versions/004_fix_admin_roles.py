"""Fix ADMIN roles to ADMINISTRADOR_GENERAL

Revision ID: 004_fix_admin_roles
Revises: 003_update_asesor_model
Create Date: 2025-10-15 15:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_fix_admin_roles'
down_revision = '003_update_asesor_model'
branch_labels = None
depends_on = None


def upgrade():
    """Update ADMIN roles to ADMINISTRADOR_GENERAL"""
    # Update existing ADMIN roles to ADMINISTRADOR_GENERAL
    op.execute("UPDATE users SET rol = 'ADMINISTRADOR_GENERAL' WHERE rol = 'ADMIN'")


def downgrade():
    """Revert ADMINISTRADOR_GENERAL roles to ADMIN"""
    # Revert ADMINISTRADOR_GENERAL roles to ADMIN
    op.execute("UPDATE users SET rol = 'ADMIN' WHERE rol = 'ADMINISTRADOR_GENERAL'")
