"""actualizar tablas concesionarios analistas modelos_vehiculos

Revision ID: 20251030_actualizar_catalogos
Revises: 20251030_columnas_prestamos
Create Date: 2025-10-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = '20251030_actualizar_catalogos'
down_revision = '20251030_columnas_prestamos'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # ============================================
    # TABLA: concesionarios
    # ============================================
    if 'concesionarios' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('concesionarios')]
        
        # Asegurar que existan todas las columnas necesarias
        if 'nombre' not in columns:
            op.add_column('concesionarios', sa.Column('nombre', sa.String(length=255), nullable=False, server_default=''))
        
        if 'activo' not in columns:
            op.add_column('concesionarios', sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'))
        
        if 'created_at' not in columns:
            op.execute(text("""
                ALTER TABLE concesionarios 
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            """))
        
        if 'updated_at' not in columns:
            op.execute(text("""
                ALTER TABLE concesionarios 
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            """))
        
        # Crear índices si no existen
        indexes = [idx['name'] for idx in inspector.get_indexes('concesionarios')]
        if 'ix_concesionarios_nombre' not in indexes:
            try:
                op.create_index('ix_concesionarios_nombre', 'concesionarios', ['nombre'])
            except Exception:
                pass
        
        print("✅ Tabla concesionarios actualizada")
    else:
        # Crear tabla si no existe
        op.create_table(
            'concesionarios',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nombre', sa.String(length=255), nullable=False),
            sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_concesionarios_nombre', 'concesionarios', ['nombre'])
        print("✅ Tabla concesionarios creada")
    
    # ============================================
    # TABLA: analistas
    # ============================================
    if 'analistas' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('analistas')]
        
        # Asegurar que existan todas las columnas necesarias
        if 'nombre' not in columns:
            op.add_column('analistas', sa.Column('nombre', sa.String(length=255), nullable=False, server_default=''))
        
        if 'activo' not in columns:
            op.add_column('analistas', sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'))
        
        if 'created_at' not in columns:
            op.execute(text("""
                ALTER TABLE analistas 
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            """))
        
        if 'updated_at' not in columns:
            op.execute(text("""
                ALTER TABLE analistas 
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            """))
        
        # Crear índices si no existen
        indexes = [idx['name'] for idx in inspector.get_indexes('analistas')]
        if 'ix_analistas_nombre' not in indexes:
            try:
                op.create_index('ix_analistas_nombre', 'analistas', ['nombre'])
            except Exception:
                pass
        
        print("✅ Tabla analistas actualizada")
    else:
        # Crear tabla si no existe
        op.create_table(
            'analistas',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nombre', sa.String(length=255), nullable=False),
            sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_analistas_nombre', 'analistas', ['nombre'])
        print("✅ Tabla analistas creada")
    
    # ============================================
    # TABLA: modelos_vehiculos
    # ============================================
    if 'modelos_vehiculos' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('modelos_vehiculos')]
        
        # Asegurar que existan todas las columnas necesarias
        if 'modelo' not in columns:
            op.add_column('modelos_vehiculos', sa.Column('modelo', sa.String(length=100), nullable=False, server_default=''))
        
        if 'activo' not in columns:
            op.add_column('modelos_vehiculos', sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'))
        
        if 'created_at' not in columns:
            op.execute(text("""
                ALTER TABLE modelos_vehiculos 
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            """))
        
        if 'updated_at' not in columns:
            op.execute(text("""
                ALTER TABLE modelos_vehiculos 
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            """))
        
        # Crear índices si no existen
        indexes = [idx['name'] for idx in inspector.get_indexes('modelos_vehiculos')]
        if 'ix_modelos_vehiculos_modelo' not in indexes:
            try:
                op.create_index('ix_modelos_vehiculos_modelo', 'modelos_vehiculos', ['modelo'])
            except Exception:
                pass
        
        if 'ix_modelos_vehiculos_activo' not in indexes:
            try:
                op.create_index('ix_modelos_vehiculos_activo', 'modelos_vehiculos', ['activo'])
            except Exception:
                pass
        
        # Verificar constraint único en modelo
        try:
            constraints = [c['name'] for c in inspector.get_unique_constraints('modelos_vehiculos')]
            constraint_names = [c for c in constraints if 'modelo' in c.lower()]
            if not constraint_names:
                op.create_unique_constraint('uq_modelos_vehiculos_modelo', 'modelos_vehiculos', ['modelo'])
        except Exception as e:
            print(f"⚠️ No se pudo crear constraint único en modelo: {e}")
        
        print("✅ Tabla modelos_vehiculos actualizada")
    else:
        # Crear tabla si no existe
        op.create_table(
            'modelos_vehiculos',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('modelo', sa.String(length=100), nullable=False),
            sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('modelo', name='uq_modelos_vehiculos_modelo')
        )
        op.create_index('ix_modelos_vehiculos_modelo', 'modelos_vehiculos', ['modelo'])
        op.create_index('ix_modelos_vehiculos_activo', 'modelos_vehiculos', ['activo'])
        print("✅ Tabla modelos_vehiculos creada")


def downgrade():
    # No hacer nada en downgrade, las tablas deben mantenerse
    pass

