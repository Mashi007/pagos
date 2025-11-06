"""crear tabla modelos vehiculos

Revision ID: 005
Revises: 004_add_total_financiamiento
Create Date: 2025-10-15 01:55:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004_add_total_financiamiento"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Verificar si la tabla ya existe
    if "modelos_vehiculos" not in inspector.get_table_names():
        # Crear tabla modelos_vehiculos
        op.create_table(
            "modelos_vehiculos",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("marca", sa.String(50), nullable=False),
            sa.Column("modelo", sa.String(100), nullable=False),
            sa.Column("nombre_completo", sa.String(150), nullable=False),
            sa.Column("categoria", sa.String(50), nullable=True),  # Sedán, SUV, Hatchback, etc.
            sa.Column("precio_base", sa.Numeric(12, 2), nullable=True),
            sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("descripcion", sa.Text(), nullable=True),
            sa.Column("especificaciones", sa.JSON(), nullable=True),  # Motor, transmisión, etc.
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("nombre_completo"),
        )
    else:
        print("Tabla 'modelos_vehiculos' ya existe")
        # Si la tabla existe, agregar columnas faltantes
        columns = [col["name"] for col in inspector.get_columns("modelos_vehiculos")]
        
        if "marca" not in columns:
            op.add_column("modelos_vehiculos", sa.Column("marca", sa.String(50), nullable=True))
        if "nombre_completo" not in columns:
            op.add_column("modelos_vehiculos", sa.Column("nombre_completo", sa.String(150), nullable=True))
        if "categoria" not in columns:
            op.add_column("modelos_vehiculos", sa.Column("categoria", sa.String(50), nullable=True))
        if "precio_base" not in columns:
            op.add_column("modelos_vehiculos", sa.Column("precio_base", sa.Numeric(12, 2), nullable=True))
        if "descripcion" not in columns:
            op.add_column("modelos_vehiculos", sa.Column("descripcion", sa.Text(), nullable=True))
        if "especificaciones" not in columns:
            op.add_column("modelos_vehiculos", sa.Column("especificaciones", sa.JSON(), nullable=True))

    # Verificar índices existentes y columnas de la tabla
    if "modelos_vehiculos" in inspector.get_table_names():
        indexes = [idx["name"] for idx in inspector.get_indexes("modelos_vehiculos")]
        columns = [col["name"] for col in inspector.get_columns("modelos_vehiculos")]
        
        # Crear índices solo si no existen Y las columnas existen
        if "ix_modelos_vehiculos_marca" not in indexes and "marca" in columns:
            op.create_index("ix_modelos_vehiculos_marca", "modelos_vehiculos", ["marca"])
        if "ix_modelos_vehiculos_modelo" not in indexes and "modelo" in columns:
            op.create_index("ix_modelos_vehiculos_modelo", "modelos_vehiculos", ["modelo"])
        if "ix_modelos_vehiculos_nombre_completo" not in indexes and "nombre_completo" in columns:
            op.create_index("ix_modelos_vehiculos_nombre_completo", "modelos_vehiculos", ["nombre_completo"])
        if "ix_modelos_vehiculos_activo" not in indexes and "activo" in columns:
            op.create_index("ix_modelos_vehiculos_activo", "modelos_vehiculos", ["activo"])

    # Nota: Los datos iniciales de modelos de vehículos pueden ser insertados
    # manualmente o a través de un script separado si es necesario.


def downgrade():
    # Eliminar índices
    op.drop_index("ix_modelos_vehiculos_activo", table_name="modelos_vehiculos")
    op.drop_index("ix_modelos_vehiculos_nombre_completo", table_name="modelos_vehiculos")
    op.drop_index("ix_modelos_vehiculos_modelo", table_name="modelos_vehiculos")
    op.drop_index("ix_modelos_vehiculos_marca", table_name="modelos_vehiculos")

    # Eliminar tabla
    op.drop_table("modelos_vehiculos")
