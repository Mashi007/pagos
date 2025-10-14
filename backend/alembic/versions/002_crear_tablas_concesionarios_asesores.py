"""Crear tablas concesionarios y asesores

Revision ID: 002
Revises: 001
Create Date: 2024-10-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla concesionarios
    op.create_table('concesionarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('direccion', sa.Text(), nullable=True),
        sa.Column('telefono', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('responsable', sa.String(length=255), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_concesionarios_id'), 'concesionarios', ['id'], unique=False)
    op.create_index(op.f('ix_concesionarios_nombre'), 'concesionarios', ['nombre'], unique=True)

    # Crear tabla asesores
    op.create_table('asesores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('apellido', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('telefono', sa.String(length=20), nullable=True),
        sa.Column('especialidad', sa.String(length=255), nullable=True),
        sa.Column('comision_porcentaje', sa.Integer(), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asesores_id'), 'asesores', ['id'], unique=False)
    op.create_index(op.f('ix_asesores_nombre'), 'asesores', ['nombre'], unique=False)
    op.create_index(op.f('ix_asesores_apellido'), 'asesores', ['apellido'], unique=False)
    op.create_index(op.f('ix_asesores_email'), 'asesores', ['email'], unique=True)

    # Insertar datos iniciales de concesionarios
    op.execute("""
        INSERT INTO concesionarios (nombre, direccion, telefono, email, responsable, activo) VALUES
        ('Concesionario Centro', 'Av. Principal, Centro', '+58-212-1234567', 'centro@concesionario.com', 'Juan Pérez', true),
        ('Auto Plaza Norte', 'Zona Norte, Caracas', '+58-212-2345678', 'norte@autoplaza.com', 'María González', true),
        ('Vehículos del Sur', 'Zona Sur, Caracas', '+58-212-3456789', 'sur@vehiculos.com', 'Carlos Rodríguez', true),
        ('Motor City', 'Chacao, Caracas', '+58-212-4567890', 'motor@city.com', 'Ana Martínez', true),
        ('Auto Express', 'La Candelaria, Caracas', '+58-212-5678901', 'express@auto.com', 'Luis Fernández', true)
    """)

    # Insertar datos iniciales de asesores
    op.execute("""
        INSERT INTO asesores (nombre, apellido, email, telefono, especialidad, comision_porcentaje, activo) VALUES
        ('María', 'González', 'maria.gonzalez@rapicredit.com', '+58-424-1234567', 'Vehículos Nuevos', 5, true),
        ('Carlos', 'Rodríguez', 'carlos.rodriguez@rapicredit.com', '+58-424-2345678', 'Vehículos Usados', 4, true),
        ('Ana', 'Martínez', 'ana.martinez@rapicredit.com', '+58-424-3456789', 'Vehículos Comerciales', 6, true),
        ('Luis', 'Fernández', 'luis.fernandez@rapicredit.com', '+58-424-4567890', 'Vehículos Nuevos', 5, true),
        ('Carmen', 'López', 'carmen.lopez@rapicredit.com', '+58-424-5678901', 'Vehículos Usados', 4, true)
    """)


def downgrade():
    # Eliminar índices
    op.drop_index(op.f('ix_asesores_email'), table_name='asesores')
    op.drop_index(op.f('ix_asesores_apellido'), table_name='asesores')
    op.drop_index(op.f('ix_asesores_nombre'), table_name='asesores')
    op.drop_index(op.f('ix_asesores_id'), table_name='asesores')
    op.drop_index(op.f('ix_concesionarios_nombre'), table_name='concesionarios')
    op.drop_index(op.f('ix_concesionarios_id'), table_name='concesionarios')
    
    # Eliminar tablas
    op.drop_table('asesores')
    op.drop_table('concesionarios')
