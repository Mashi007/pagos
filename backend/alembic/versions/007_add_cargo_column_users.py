"""Agregar columna cargo a tabla usuarios

Revision ID: 007_add_cargo_column_users
Revises: 006_update_user_roles_system
Create Date: 2025-10-17 20:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_add_cargo_column_users'
down_revision = '006_update_user_roles_system'
branch_labels = None
depends_on = None


def upgrade():
    """Agregar columna cargo a la tabla usuarios si no existe"""
    # Verificar si la columna ya existe antes de agregarla
    connection = op.get_bind()
    
    # Verificar si la columna cargo existe
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'usuarios' 
        AND column_name = 'cargo'
    """))
    
    if not result.fetchone():
        # La columna no existe, agregarla
        op.add_column('usuarios', sa.Column('cargo', sa.String(length=100), nullable=True))
        print("Columna 'cargo' agregada a tabla 'usuarios'")
    else:
        print("Columna 'cargo' ya existe en tabla 'usuarios'")


def downgrade():
    """Eliminar columna cargo de la tabla usuarios"""
    # Verificar si la columna existe antes de eliminarla
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'usuarios' 
        AND column_name = 'cargo'
    """))
    
    if result.fetchone():
        # La columna existe, eliminarla
        op.drop_column('usuarios', 'cargo')
        print("Columna 'cargo' eliminada de tabla 'usuarios'")
    else:
        print("Columna 'cargo' no existe en tabla 'usuarios'")
