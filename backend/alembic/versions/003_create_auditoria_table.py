"""create auditoria table

Revision ID: 003_create_auditoria_table
Revises: 001_cliente_vehicular
Create Date: 2025-01-15 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_create_auditoria_table"
down_revision = "001_cliente_vehicular"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Verificar si la tabla ya existe
    if "auditoria" not in inspector.get_table_names():
        # Crear tabla de auditoría (singular, como en el modelo)
        op.create_table(
            "auditoria",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("accion", sa.String(length=50), nullable=False),
            sa.Column("entidad", sa.String(length=50), nullable=False),
            sa.Column("entidad_id", sa.Integer(), nullable=True),
            sa.Column("detalles", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("exito", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("mensaje_error", sa.Text(), nullable=True),
            sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["usuario_id"], ["users.id"]),
        )
    else:
        print("Tabla 'auditoria' ya existe")

    # Verificar índices existentes
    indexes = [idx["name"] for idx in inspector.get_indexes("auditoria")] if "auditoria" in inspector.get_table_names() else []
    
    # Crear índices para optimizar consultas solo si no existen
    if "ix_auditoria_id" not in indexes:
        op.create_index("ix_auditoria_id", "auditoria", ["id"], unique=False)
    if "ix_auditoria_usuario_id" not in indexes:
        op.create_index("ix_auditoria_usuario_id", "auditoria", ["usuario_id"], unique=False)
    if "ix_auditoria_accion" not in indexes:
        op.create_index("ix_auditoria_accion", "auditoria", ["accion"], unique=False)
    if "ix_auditoria_entidad" not in indexes:
        op.create_index("ix_auditoria_entidad", "auditoria", ["entidad"], unique=False)
    if "ix_auditoria_entidad_id" not in indexes:
        op.create_index("ix_auditoria_entidad_id", "auditoria", ["entidad_id"], unique=False)
    if "ix_auditoria_fecha" not in indexes:
        op.create_index("ix_auditoria_fecha", "auditoria", ["fecha"], unique=False)


def downgrade():
    # Eliminar índices
    op.drop_index("ix_auditoria_fecha", table_name="auditoria")
    op.drop_index("ix_auditoria_entidad_id", table_name="auditoria")
    op.drop_index("ix_auditoria_entidad", table_name="auditoria")
    op.drop_index("ix_auditoria_accion", table_name="auditoria")
    op.drop_index("ix_auditoria_usuario_id", table_name="auditoria")
    op.drop_index("ix_auditoria_id", table_name="auditoria")

    # Eliminar tabla
    op.drop_table("auditoria")
