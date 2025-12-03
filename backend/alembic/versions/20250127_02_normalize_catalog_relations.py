"""normalize catalog relations in prestamos table

Revision ID: 20250127_02_normalize_catalogs
Revises: 20250127_01_critical_fks
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20250127_02_normalize_catalogs'
down_revision = '20250127_01_critical_fks'
branch_labels = None
depends_on = None


def upgrade():
    """
    Normalizar relaciones de catálogos en tabla prestamos:
    1. concesionario (string) → concesionario_id (FK)
    2. analista (string) → analista_id (FK)
    3. modelo_vehiculo (string) → modelo_vehiculo_id (FK)
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    # Verificar que las tablas existan
    required_tables = ['prestamos', 'concesionarios', 'analistas', 'modelos_vehiculos']
    for table in required_tables:
        if table not in inspector.get_table_names():
            print(f"⚠️ Tabla '{table}' no existe, saltando migración")
            return

    prestamos_columns = [col['name'] for col in inspector.get_columns('prestamos')]

    # 1. Normalizar concesionario → concesionario_id
    if 'concesionario_id' not in prestamos_columns:
        print("✅ Agregando columna concesionario_id a tabla prestamos...")
        op.add_column('prestamos', sa.Column('concesionario_id', sa.Integer(), nullable=True))
        
        # Poblar concesionario_id basado en nombre
        print("✅ Poblando concesionario_id basado en nombre...")
        op.execute("""
            UPDATE prestamos p
            SET concesionario_id = (
                SELECT c.id 
                FROM concesionarios c 
                WHERE c.nombre = p.concesionario 
                LIMIT 1
            )
            WHERE concesionario IS NOT NULL;
        """)
        
        # Crear índice y ForeignKey
        op.create_index('ix_prestamos_concesionario_id', 'prestamos', ['concesionario_id'])
        
        try:
            op.create_foreign_key(
                'fk_prestamos_concesionario',
                'prestamos',
                'concesionarios',
                ['concesionario_id'],
                ['id'],
                ondelete='SET NULL'
            )
            print("✅ Columna concesionario_id agregada y FK creado")
        except Exception as e:
            print(f"⚠️ Error al crear FK concesionario_id: {e}")

    # 2. Normalizar analista → analista_id
    if 'analista_id' not in prestamos_columns:
        print("✅ Agregando columna analista_id a tabla prestamos...")
        op.add_column('prestamos', sa.Column('analista_id', sa.Integer(), nullable=True))
        
        # Poblar analista_id basado en nombre
        print("✅ Poblando analista_id basado en nombre...")
        op.execute("""
            UPDATE prestamos p
            SET analista_id = (
                SELECT a.id 
                FROM analistas a 
                WHERE a.nombre = p.analista 
                LIMIT 1
            )
            WHERE analista IS NOT NULL;
        """)
        
        # Crear índice y ForeignKey
        op.create_index('ix_prestamos_analista_id', 'prestamos', ['analista_id'])
        
        try:
            op.create_foreign_key(
                'fk_prestamos_analista',
                'prestamos',
                'analistas',
                ['analista_id'],
                ['id'],
                ondelete='SET NULL'
            )
            print("✅ Columna analista_id agregada y FK creado")
        except Exception as e:
            print(f"⚠️ Error al crear FK analista_id: {e}")

    # 3. Normalizar modelo_vehiculo → modelo_vehiculo_id
    if 'modelo_vehiculo_id' not in prestamos_columns:
        print("✅ Agregando columna modelo_vehiculo_id a tabla prestamos...")
        op.add_column('prestamos', sa.Column('modelo_vehiculo_id', sa.Integer(), nullable=True))
        
        # Poblar modelo_vehiculo_id basado en modelo
        print("✅ Poblando modelo_vehiculo_id basado en modelo...")
        op.execute("""
            UPDATE prestamos p
            SET modelo_vehiculo_id = (
                SELECT mv.id 
                FROM modelos_vehiculos mv 
                WHERE mv.modelo = p.modelo_vehiculo 
                LIMIT 1
            )
            WHERE modelo_vehiculo IS NOT NULL;
        """)
        
        # Crear índice y ForeignKey
        op.create_index('ix_prestamos_modelo_vehiculo_id', 'prestamos', ['modelo_vehiculo_id'])
        
        try:
            op.create_foreign_key(
                'fk_prestamos_modelo_vehiculo',
                'prestamos',
                'modelos_vehiculos',
                ['modelo_vehiculo_id'],
                ['id'],
                ondelete='SET NULL'
            )
            print("✅ Columna modelo_vehiculo_id agregada y FK creado")
        except Exception as e:
            print(f"⚠️ Error al crear FK modelo_vehiculo_id: {e}")


def downgrade():
    """Revertir normalización de catálogos"""
    connection = op.get_bind()
    inspector = inspect(connection)

    prestamos_columns = [col['name'] for col in inspector.get_columns('prestamos')]

    # Eliminar ForeignKeys y columnas en orden inverso
    if 'modelo_vehiculo_id' in prestamos_columns:
        try:
            op.drop_constraint('fk_prestamos_modelo_vehiculo', 'prestamos', type_='foreignkey')
            op.drop_index('ix_prestamos_modelo_vehiculo_id', table_name='prestamos')
            op.drop_column('prestamos', 'modelo_vehiculo_id')
            print("✅ Columna modelo_vehiculo_id eliminada")
        except Exception:
            pass

    if 'analista_id' in prestamos_columns:
        try:
            op.drop_constraint('fk_prestamos_analista', 'prestamos', type_='foreignkey')
            op.drop_index('ix_prestamos_analista_id', table_name='prestamos')
            op.drop_column('prestamos', 'analista_id')
            print("✅ Columna analista_id eliminada")
        except Exception:
            pass

    if 'concesionario_id' in prestamos_columns:
        try:
            op.drop_constraint('fk_prestamos_concesionario', 'prestamos', type_='foreignkey')
            op.drop_index('ix_prestamos_concesionario_id', table_name='prestamos')
            op.drop_column('prestamos', 'concesionario_id')
            print("✅ Columna concesionario_id eliminada")
        except Exception:
            pass

