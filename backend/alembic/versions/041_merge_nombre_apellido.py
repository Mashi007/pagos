"""Merge nombre and apellido columns, remove apellido

Revision ID: 041_merge_nombre_apellido
Revises: 040_add_cedula_to_usuarios
Create Date: 2026-04-01 01:30:00.000000

Merges apellido into nombre column (full name) and removes apellido column.
Expands nombre to VARCHAR(255) to accommodate full name.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '041_merge_nombre_apellido'
down_revision = '040_add_cedula_to_usuarios'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Extend nombre column to accommodate full name
    op.alter_column('usuarios', 'nombre', 
                   existing_type=sa.String(100),
                   type_=sa.String(255),
                   existing_nullable=False,
                   nullable=False)
    
    # 2. Merge apellido into nombre
    op.execute("""
        UPDATE usuarios 
        SET nombre = TRIM(nombre || ' ' || COALESCE(apellido, ''))
        WHERE apellido IS NOT NULL AND apellido != ''
    """)
    
    # 3. Drop apellido column
    op.drop_column('usuarios', 'apellido')
    
    # 4. Update comment for documentation
    op.execute("""
        COMMENT ON COLUMN usuarios.nombre IS 
        'Full name (nombre completo - nombre y apellido)'
    """)


def downgrade() -> None:
    # 1. Add apellido column back
    op.add_column('usuarios', sa.Column('apellido', sa.String(100), 
                                       server_default=sa.text("''"), 
                                       nullable=False))
    
    # 2. Split nombre back into nombre and apellido (split at last space)
    op.execute("""
        UPDATE usuarios 
        SET apellido = SUBSTRING(nombre FROM POSITION(' ' IN nombre) + 1),
            nombre = SUBSTRING(nombre FROM 1 FOR POSITION(' ' IN nombre) - 1)
        WHERE nombre LIKE '% %'
    """)
    
    # 3. Restore nombre column size
    op.alter_column('usuarios', 'nombre',
                   existing_type=sa.String(255),
                   type_=sa.String(100),
                   existing_nullable=False,
                   nullable=False)
