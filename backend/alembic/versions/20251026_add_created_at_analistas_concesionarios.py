"""Add created_at to analistas and concesionarios

Revision ID: add_created_at_analistas_concesionarios
Revises: 017_add_is_admin_column
Create Date: 2025-10-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'add_created_at_anal_conces'
down_revision = '017_add_is_admin_column'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar created_at a analistas
    op.execute(text("""
        ALTER TABLE analistas 
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT '2025-10-01 00:00:00+00'::timestamptz
    """))
    
    op.execute(text("""
        ALTER TABLE analistas 
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    """))
    
    # Actualizar registros existentes sin created_at
    op.execute(text("""
        UPDATE analistas 
        SET created_at = '2025-10-01 00:00:00+00'::timestamptz 
        WHERE created_at IS NULL
    """))
    
    # Agregar created_at a concesionarios
    op.execute(text("""
        ALTER TABLE concesionarios 
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT '2025-10-01 00:00:00+00'::timestamptz
    """))
    
    # Actualizar registros existentes sin created_at
    op.execute(text("""
        UPDATE concesionarios 
        SET created_at = '2025-10-01 00:00:00+00'::timestamptz 
        WHERE created_at IS NULL
    """))


def downgrade():
    op.execute(text("ALTER TABLE analistas DROP COLUMN IF EXISTS created_at"))
    op.execute(text("ALTER TABLE analistas DROP COLUMN IF EXISTS updated_at"))
    op.execute(text("ALTER TABLE concesionarios DROP COLUMN IF EXISTS created_at"))

