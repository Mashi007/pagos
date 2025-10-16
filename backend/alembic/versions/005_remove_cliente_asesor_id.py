"""remove cliente asesor_id column

Revision ID: 005_remove_cliente_asesor_id
Revises: 004_fix_admin_roles
Create Date: 2025-10-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_remove_cliente_asesor_id'
down_revision = '004_fix_admin_roles'
branch_labels = None
depends_on = None


def upgrade():
    """
    Eliminar columna asesor_id de tabla clientes
    Esta columna creaba una relación incorrecta con la tabla users
    Los clientes deben relacionarse solo con asesores de configuración via asesor_id
    """
    # Verificar si la columna existe antes de eliminarla
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name='clientes' AND column_name='asesor_id'
            ) THEN
                ALTER TABLE clientes DROP COLUMN asesor_id;
            END IF;
        END $$;
    """)


def downgrade():
    """
    Restaurar columna asesor_id si se necesita revertir
    """
    op.add_column(
        'clientes',
        sa.Column('asesor_id', sa.Integer(), nullable=True)
    )
    op.create_index('ix_clientes_asesor_id', 'clientes', ['asesor_id'])
    op.create_foreign_key(
        'fk_clientes_asesor_id_users',
        'clientes', 'users',
        ['asesor_id'], ['id']
    )

