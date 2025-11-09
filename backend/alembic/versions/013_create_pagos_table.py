"""create pagos table

Revision ID: 013_create_pagos_table
Revises: 012_add_concesionario_analista_clientes
Create Date: 2025-10-19 10:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "013_create_pagos_table"
down_revision = "012_add_conces_anal_clientes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    # Verificar si la tabla ya existe
    if "pagos" in inspector.get_table_names():
        return

    op.create_table(
        "pagos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cedula_cliente", sa.String(length=20), nullable=False),
        sa.Column("fecha_pago", sa.DateTime(), nullable=False),
        sa.Column("monto_pagado", sa.Float(), nullable=False),
        sa.Column("numero_documento", sa.String(length=100), nullable=False),
        sa.Column("documento_nombre", sa.String(length=255), nullable=True),
        sa.Column("documento_tipo", sa.String(length=10), nullable=True),
        sa.Column("documento_tamaño", sa.Integer(), nullable=True),
        sa.Column("documento_ruta", sa.String(length=500), nullable=True),
        sa.Column("conciliado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("fecha_conciliacion", sa.DateTime(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Verificar índices existentes y columnas de la tabla
    indexes = [idx["name"] for idx in inspector.get_indexes("pagos")]
    columns = [col["name"] for col in inspector.get_columns("pagos")]

    # Crear índices solo si no existen Y las columnas existen
    if "ix_pagos_cedula_cliente" not in indexes and "cedula_cliente" in columns:
        op.create_index("ix_pagos_cedula_cliente", "pagos", ["cedula_cliente"])
    if "ix_pagos_fecha_pago" not in indexes and "fecha_pago" in columns:
        op.create_index("ix_pagos_fecha_pago", "pagos", ["fecha_pago"])
    if "ix_pagos_conciliado" not in indexes and "conciliado" in columns:
        op.create_index("ix_pagos_conciliado", "pagos", ["conciliado"])
    if "ix_pagos_activo" not in indexes and "activo" in columns:
        op.create_index("ix_pagos_activo", "pagos", ["activo"])


def downgrade() -> None:
    # Eliminar índices
    op.drop_index("ix_pagos_activo", table_name="pagos")
    op.drop_index("ix_pagos_conciliado", table_name="pagos")
    op.drop_index("ix_pagos_fecha_pago", table_name="pagos")
    op.drop_index("ix_pagos_cedula_cliente", table_name="pagos")

    # Eliminar tabla
    op.drop_table("pagos")
