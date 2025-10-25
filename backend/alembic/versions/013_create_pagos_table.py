
Revises: 012_add_concesionario_analista_clientes
Create Date: 2025-10-19 10:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
down_revision = "012_add_concesionario_analista_clientes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    # Verificar si la tabla ya existe
        return

    op.create_table(
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cedula_cliente", sa.String(length=20), nullable=False),
        sa.Column("fecha_pago", sa.DateTime(), nullable=False),
        sa.Column("monto_pagado", sa.Float(), nullable=False),
        sa.Column("numero_documento", sa.String(length=100), nullable=False),
        sa.Column("documento_nombre", sa.String(length=255), nullable=True),
        sa.Column("documento_tipo", sa.String(length=10), nullable=True),
        sa.Column("documento_tamaño", sa.Integer(), nullable=True),
        sa.Column("documento_ruta", sa.String(length=500), nullable=True),
        sa.Column("conciliado", sa.Boolean(), nullable=False, default=False),
        sa.Column("fecha_conciliacion", sa.DateTime(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, default=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "fecha_registro",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Crear índices



def downgrade() -> None:
