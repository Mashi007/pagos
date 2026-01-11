"""agregar campo requiere_revision a prestamos

Revision ID: 20260112_requiere_revision
Revises: 20260111_fase3_sync
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20260112_requiere_revision'
down_revision = '20260111_fase3_sync'
branch_labels = None
depends_on = None


def upgrade():
    """
    Agregar campo requiere_revision (boolean) a tabla prestamos.
    Este campo permite marcar préstamos que necesitan revisión manual
    de diferencias en abonos.
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'prestamos' not in inspector.get_table_names():
        print("⚠️ Tabla 'prestamos' no existe, saltando migración")
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos')]

    # Agregar columna requiere_revision si no existe
    if 'requiere_revision' not in columns:
        op.add_column('prestamos', sa.Column('requiere_revision', sa.Boolean(), nullable=False, server_default='false'))
        print("✅ Columna 'requiere_revision' agregada a tabla prestamos")

    # Crear índice para mejorar consultas de préstamos que requieren revisión
    try:
        op.create_index('ix_prestamos_requiere_revision', 'prestamos', ['requiere_revision'])
        print("✅ Índice 'ix_prestamos_requiere_revision' creado")
    except Exception as e:
        print(f"⚠️ No se pudo crear índice (puede que ya exista): {e}")


def downgrade():
    """Eliminar campo requiere_revision"""
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'prestamos' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos')]

    # Eliminar índice
    try:
        op.drop_index('ix_prestamos_requiere_revision', table_name='prestamos')
        print("✅ Índice 'ix_prestamos_requiere_revision' eliminado")
    except Exception:
        pass

    # Eliminar columna
    if 'requiere_revision' in columns:
        op.drop_column('prestamos', 'requiere_revision')
        print("✅ Columna 'requiere_revision' eliminada de tabla prestamos")
