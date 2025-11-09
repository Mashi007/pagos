"""agregar cedula a evaluacion

Revision ID: agregar_cedula
Revises: add_referencias_individuales, add_notificacion_plantillas
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'agregar_cedula'
down_revision = ('add_referencias_individuales', 'add_notificacion_plantillas')
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if 'prestamos_evaluacion' not in inspector.get_table_names():
        print("⚠️ Tabla 'prestamos_evaluacion' no existe, saltando migración")
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos_evaluacion')]

    # Agregar columna cedula a la tabla prestamos_evaluacion si no existe
    if 'cedula' not in columns:
        op.add_column('prestamos_evaluacion', sa.Column('cedula', sa.String(length=20), nullable=True))

    # Crear índice para búsquedas rápidas por cédula
    indexes = [idx['name'] for idx in inspector.get_indexes('prestamos_evaluacion')]
    if 'ix_prestamos_evaluacion_cedula' not in indexes:
        op.create_index('ix_prestamos_evaluacion_cedula', 'prestamos_evaluacion', ['cedula'], unique=False)

    # Actualizar registros existentes con la cédula desde la tabla prestamos
    if 'prestamos' in inspector.get_table_names():
        try:
            op.execute(sa.text("""
                UPDATE prestamos_evaluacion e
                SET cedula = p.cedula
                FROM prestamos p
                WHERE e.prestamo_id = p.id;
            """))
        except Exception as e:
            print(f"⚠️ No se pudo actualizar cédulas desde prestamos: {e}")

    # Hacer la columna NOT NULL después de poblarla
    try:
        op.alter_column('prestamos_evaluacion', 'cedula', nullable=False)
    except Exception as e:
        print(f"⚠️ No se pudo hacer la columna NOT NULL: {e}")


def downgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if 'prestamos_evaluacion' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('prestamos_evaluacion')]
    indexes = [idx['name'] for idx in inspector.get_indexes('prestamos_evaluacion')]

    # Eliminar índice si existe
    if 'ix_prestamos_evaluacion_cedula' in indexes:
        try:
            op.drop_index('ix_prestamos_evaluacion_cedula', table_name='prestamos_evaluacion')
        except Exception as e:
            print(f"⚠️ No se pudo eliminar índice: {e}")

    # Eliminar columna si existe
    if 'cedula' in columns:
        op.drop_column('prestamos_evaluacion', 'cedula')
