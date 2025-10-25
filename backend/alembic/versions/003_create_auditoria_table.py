
Revision ID: 003_create_auditoria_table
Revises: 002_add_cliente_foreignkeys
Create Date: 2025-01-15 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_create_auditoria_table"
down_revision = "002_add_cliente_foreignkeys"
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla de auditoría
    op.create_table
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("usuario_email", sa.String(length=255), nullable=True),
        sa.Column("accion", sa.String(length=50), nullable=False),
        sa.Column("modulo", sa.String(length=50), nullable=False),
        sa.Column("tabla", sa.String(length=50), nullable=False),
        sa.Column("registro_id", sa.Integer(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column
        sa.Column
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("resultado", sa.String(length=20), nullable=False),
        sa.Column("mensaje_error", sa.Text(), nullable=True),
        sa.Column
            server_default=sa.text("now()"),
            nullable=False,
        sa.PrimaryKeyConstraint("id"),

    # Crear índices para optimizar consultas
    op.create_index(op.f("ix_auditorias_id"), "auditorias", ["id"], unique=False)
    op.create_index
        op.f("ix_auditorias_usuario_id"), "auditorias", ["usuario_id"], unique=False
    op.create_index
        op.f("ix_auditorias_usuario_email"),
        "auditorias",
        ["usuario_email"],
        unique=False,
    op.create_index
        op.f("ix_auditorias_accion"), "auditorias", ["accion"], unique=False
    op.create_index
        op.f("ix_auditorias_modulo"), "auditorias", ["modulo"], unique=False
    op.create_index(op.f("ix_auditorias_tabla"), "auditorias", ["tabla"], unique=False)
    op.create_index
        op.f("ix_auditorias_registro_id"), "auditorias", ["registro_id"], unique=False
    op.create_index(op.f("ix_auditorias_fecha"), "auditorias", ["fecha"], unique=False)


def downgrade():
    # Eliminar índices
    op.drop_index(op.f("ix_auditorias_fecha"), table_name="auditorias")
    op.drop_index(op.f("ix_auditorias_registro_id"), table_name="auditorias")
    op.drop_index(op.f("ix_auditorias_tabla"), table_name="auditorias")
    op.drop_index(op.f("ix_auditorias_modulo"), table_name="auditorias")
    op.drop_index(op.f("ix_auditorias_accion"), table_name="auditorias")
    op.drop_index(op.f("ix_auditorias_usuario_email"), table_name="auditorias")
    op.drop_index(op.f("ix_auditorias_usuario_id"), table_name="auditorias")
    op.drop_index(op.f("ix_auditorias_id"), table_name="auditorias")

    # Eliminar tabla
    op.drop_table("auditorias")

"""