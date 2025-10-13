"""corregir foreign keys cliente prestamo

Revision ID: 002_corregir_foreign_keys_cliente_prestamo
Revises: 001_expandir_cliente_financiamiento
Create Date: 2025-01-13 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_corregir_foreign_keys_cliente_prestamo'
down_revision = '001_expandir_cliente_financiamiento'
branch_labels = None
depends_on = None


def upgrade():
    """Corregir foreign key de prestamos.cliente_id para que apunte a clientes.id"""
    
    # Primero, eliminar la foreign key existente incorrecta
    op.drop_constraint('prestamos_cliente_id_fkey', 'prestamos', type_='foreignkey')
    
    # Crear la nueva foreign key correcta
    op.create_foreign_key(
        'prestamos_cliente_id_fkey',
        'prestamos', 'clientes',
        ['cliente_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    """Revertir cambios"""
    
    # Eliminar la foreign key correcta
    op.drop_constraint('prestamos_cliente_id_fkey', 'prestamos', type_='foreignkey')
    
    # Restaurar la foreign key incorrecta (si es necesario)
    op.create_foreign_key(
        'prestamos_cliente_id_fkey',
        'prestamos', 'users',
        ['cliente_id'], ['id'],
        ondelete='CASCADE'
    )
