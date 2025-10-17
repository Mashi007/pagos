"""Actualizar sistema de roles para usuarios

Revision ID: 006_update_user_roles_system
Revises: 005_crear_tabla_modelos_vehiculos
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_update_user_roles_system'
down_revision = '005_crear_tabla_modelos_vehiculos'
branch_labels = None
depends_on = None


def upgrade():
    # Crear nuevo enum con los roles actualizados
    op.execute("CREATE TYPE userrole_new AS ENUM ('USER', 'ADMIN', 'GERENTE', 'COBRANZAS')")
    
    # Agregar columna cargo si no existe
    op.add_column('usuarios', sa.Column('cargo', sa.String(length=100), nullable=True))
    
    # Actualizar columna rol para usar el nuevo enum
    op.execute("ALTER TABLE usuarios ALTER COLUMN rol TYPE userrole_new USING rol::text::userrole_new")
    
    # Eliminar el enum viejo
    op.execute("DROP TYPE userrole")
    
    # Renombrar el nuevo enum
    op.execute("ALTER TYPE userrole_new RENAME TO userrole")
    
    # Crear índices si no existen
    op.create_index(op.f('ix_usuarios_cargo'), 'usuarios', ['cargo'], unique=False)


def downgrade():
    # Revertir cambios
    op.drop_index(op.f('ix_usuarios_cargo'), table_name='usuarios')
    op.drop_column('usuarios', 'cargo')
    
    # Revertir enum
    op.execute("CREATE TYPE userrole_old AS ENUM ('USER')")
    op.execute("ALTER TABLE usuarios ALTER COLUMN rol TYPE userrole_old USING rol::text::userrole_old")
    op.execute("DROP TYPE userrole")
    op.execute("ALTER TYPE userrole_old RENAME TO userrole")
