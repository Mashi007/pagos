"""verificar estado de foreign keys

Revision ID: 003_verificar_foreign_keys
Revises: 002_corregir_foreign_keys_cliente_prestamo
Create Date: 2025-01-13 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_verificar_foreign_keys'
down_revision = '002_corregir_foreign_keys_cliente_prestamo'
branch_labels = None
depends_on = None


def upgrade():
    """Verificar y corregir foreign keys si es necesario"""
    
    # Verificar si la foreign key existe y está correcta
    connection = op.get_bind()
    
    # Obtener información de foreign keys existentes
    result = connection.execute(sa.text("""
        SELECT 
            tc.constraint_name, 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' 
        AND tc.table_name = 'prestamos'
        AND kcu.column_name = 'cliente_id'
    """))
    
    foreign_keys = result.fetchall()
    
    # Si no hay foreign key o está incorrecta, corregirla
    if not foreign_keys or not any(fk[3] == 'clientes' for fk in foreign_keys):
        # Eliminar foreign key existente si existe
        try:
            op.drop_constraint('prestamos_cliente_id_fkey', 'prestamos', type_='foreignkey')
        except:
            pass  # La constraint no existe
        
        # Crear la foreign key correcta
        op.create_foreign_key(
            'prestamos_cliente_id_fkey',
            'prestamos', 'clientes',
            ['cliente_id'], ['id'],
            ondelete='CASCADE'
        )


def downgrade():
    """Revertir cambios"""
    pass  # No hacer nada en downgrade
