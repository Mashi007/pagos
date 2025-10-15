"""Crear tabla de modelos de vehículos configurables

Revision ID: 005
Revises: 004
Create Date: 2025-10-15 01:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Crear tabla de modelos de vehículos"""
    
    # Crear tabla modelos_vehiculos
    op.create_table('modelos_vehiculos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('marca', sa.String(50), nullable=False),
        sa.Column('modelo', sa.String(100), nullable=False),
        sa.Column('nombre_completo', sa.String(150), nullable=False),
        sa.Column('categoria', sa.String(50), nullable=True),  # Sedán, SUV, Hatchback, etc.
        sa.Column('precio_base', sa.Numeric(12, 2), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, default=True),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('especificaciones', sa.JSON(), nullable=True),  # Motor, transmisión, etc.
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre_completo')
    )
    
    # Crear índices
    op.create_index('idx_modelos_vehiculos_marca', 'modelos_vehiculos', ['marca'])
    op.create_index('idx_modelos_vehiculos_categoria', 'modelos_vehiculos', ['categoria'])
    op.create_index('idx_modelos_vehiculos_activo', 'modelos_vehiculos', ['activo'])
    
    # Insertar datos iniciales
    modelos_iniciales = [
        # Toyota
        {'marca': 'Toyota', 'modelo': 'Corolla', 'nombre_completo': 'Toyota Corolla', 'categoria': 'Sedán', 'precio_base': 25000.00},
        {'marca': 'Toyota', 'modelo': 'Camry', 'nombre_completo': 'Toyota Camry', 'categoria': 'Sedán', 'precio_base': 32000.00},
        {'marca': 'Toyota', 'modelo': 'RAV4', 'nombre_completo': 'Toyota RAV4', 'categoria': 'SUV', 'precio_base': 35000.00},
        {'marca': 'Toyota', 'modelo': 'Hilux', 'nombre_completo': 'Toyota Hilux', 'categoria': 'Pickup', 'precio_base': 40000.00},
        
        # Nissan
        {'marca': 'Nissan', 'modelo': 'Versa', 'nombre_completo': 'Nissan Versa', 'categoria': 'Sedán', 'precio_base': 18000.00},
        {'marca': 'Nissan', 'modelo': 'Sentra', 'nombre_completo': 'Nissan Sentra', 'categoria': 'Sedán', 'precio_base': 22000.00},
        {'marca': 'Nissan', 'modelo': 'X-Trail', 'nombre_completo': 'Nissan X-Trail', 'categoria': 'SUV', 'precio_base': 30000.00},
        {'marca': 'Nissan', 'modelo': 'Frontier', 'nombre_completo': 'Nissan Frontier', 'categoria': 'Pickup', 'precio_base': 28000.00},
        
        # Chevrolet
        {'marca': 'Chevrolet', 'modelo': 'Aveo', 'nombre_completo': 'Chevrolet Aveo', 'categoria': 'Sedán', 'precio_base': 16000.00},
        {'marca': 'Chevrolet', 'modelo': 'Cruze', 'nombre_completo': 'Chevrolet Cruze', 'categoria': 'Sedán', 'precio_base': 20000.00},
        {'marca': 'Chevrolet', 'modelo': 'Equinox', 'nombre_completo': 'Chevrolet Equinox', 'categoria': 'SUV', 'precio_base': 28000.00},
        {'marca': 'Chevrolet', 'modelo': 'Colorado', 'nombre_completo': 'Chevrolet Colorado', 'categoria': 'Pickup', 'precio_base': 32000.00},
        
        # Ford
        {'marca': 'Ford', 'modelo': 'Fiesta', 'nombre_completo': 'Ford Fiesta', 'categoria': 'Hatchback', 'precio_base': 15000.00},
        {'marca': 'Ford', 'modelo': 'Focus', 'nombre_completo': 'Ford Focus', 'categoria': 'Sedán', 'precio_base': 19000.00},
        {'marca': 'Ford', 'modelo': 'Escape', 'nombre_completo': 'Ford Escape', 'categoria': 'SUV', 'precio_base': 26000.00},
        {'marca': 'Ford', 'modelo': 'Ranger', 'nombre_completo': 'Ford Ranger', 'categoria': 'Pickup', 'precio_base': 30000.00},
        
        # Hyundai
        {'marca': 'Hyundai', 'modelo': 'Accent', 'nombre_completo': 'Hyundai Accent', 'categoria': 'Sedán', 'precio_base': 17000.00},
        {'marca': 'Hyundai', 'modelo': 'Elantra', 'nombre_completo': 'Hyundai Elantra', 'categoria': 'Sedán', 'precio_base': 21000.00},
        {'marca': 'Hyundai', 'modelo': 'Tucson', 'nombre_completo': 'Hyundai Tucson', 'categoria': 'SUV', 'precio_base': 27000.00},
        {'marca': 'Hyundai', 'modelo': 'Santa Fe', 'nombre_completo': 'Hyundai Santa Fe', 'categoria': 'SUV', 'precio_base': 35000.00},
        
        # Kia
        {'marca': 'Kia', 'modelo': 'Rio', 'nombre_completo': 'Kia Rio', 'categoria': 'Sedán', 'precio_base': 16000.00},
        {'marca': 'Kia', 'modelo': 'Forte', 'nombre_completo': 'Kia Forte', 'categoria': 'Sedán', 'precio_base': 20000.00},
        {'marca': 'Kia', 'modelo': 'Sportage', 'nombre_completo': 'Kia Sportage', 'categoria': 'SUV', 'precio_base': 25000.00},
        {'marca': 'Kia', 'modelo': 'Sorento', 'nombre_completo': 'Kia Sorento', 'categoria': 'SUV', 'precio_base': 32000.00},
        
        # Motocicletas
        {'marca': 'Honda', 'modelo': 'CB 125F', 'nombre_completo': 'Honda CB 125F', 'categoria': 'Motocicleta', 'precio_base': 3500.00},
        {'marca': 'Yamaha', 'modelo': 'YZF-R3', 'nombre_completo': 'Yamaha YZF-R3', 'categoria': 'Motocicleta', 'precio_base': 6000.00},
        {'marca': 'Suzuki', 'modelo': 'GSX-R150', 'nombre_completo': 'Suzuki GSX-R150', 'categoria': 'Motocicleta', 'precio_base': 4500.00},
        {'marca': 'Kawasaki', 'modelo': 'Ninja 300', 'nombre_completo': 'Kawasaki Ninja 300', 'categoria': 'Motocicleta', 'precio_base': 7000.00},
    ]
    
    # Insertar modelos
    for modelo in modelos_iniciales:
        op.execute(
            sa.text("""
                INSERT INTO modelos_vehiculos (marca, modelo, nombre_completo, categoria, precio_base, activo, created_at, updated_at)
                VALUES (:marca, :modelo, :nombre_completo, :categoria, :precio_base, true, now(), now())
                ON CONFLICT (nombre_completo) DO NOTHING
            """).bindparam(**modelo)
        )


def downgrade():
    """Eliminar tabla de modelos de vehículos"""
    op.drop_table('modelos_vehiculos')
