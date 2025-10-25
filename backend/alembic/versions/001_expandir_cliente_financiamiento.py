
Revision ID: 001_cliente_vehicular
Revises:
Create Date: 2024-10-12 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_cliente_vehicular"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(
        "clientes", sa.Column("modelo_vehiculo", sa.String(100), nullable=True)
    )
    op.add_column("clientes", sa.Column("concesionario", sa.String(100), nullable=True))
    op.add_column(
        "clientes", sa.Column("total_financiamiento", sa.Numeric(12, 2), nullable=True)
    )
    op.add_column(
        "clientes", sa.Column("cuota_inicial", sa.Numeric(12, 2), server_default="0.00")
    )
    op.add_column("clientes", sa.Column("fecha_entrega", sa.Date(), nullable=True))
    op.add_column(
        "clientes", sa.Column("numero_amortizaciones", sa.Integer(), nullable=True)
    )
    op.add_column(
        "clientes",
        sa.Column("modalidad_financiamiento", sa.String(20), server_default="MENSUAL"),
    )
    op.add_column("clientes", sa.Column("asesor_id", sa.Integer(), nullable=True))
    op.add_column("clientes", sa.Column("dias_mora", sa.Integer(), server_default="0"))
    op.add_column(
        "clientes",
        sa.Column("saldo_pendiente_total", sa.Numeric(12, 2), server_default="0.00"),
    )

    # Crear índices para mejorar performance de búsquedas
    op.create_index("idx_clientes_telefono", "clientes", ["telefono"])
    op.create_index("idx_clientes_email", "clientes", ["email"])
    op.create_index("idx_clientes_modelo_vehiculo", "clientes", ["modelo_vehiculo"])
    op.create_index("idx_clientes_concesionario", "clientes", ["concesionario"])
    op.create_index(
        "idx_clientes_modalidad_financiamiento",
        "clientes",
        ["modalidad_financiamiento"],
    )
    op.create_index("idx_clientes_asesor_id", "clientes", ["asesor_id"])
    op.create_index("idx_clientes_estado", "clientes", ["estado"])
    op.create_index("idx_clientes_dias_mora", "clientes", ["dias_mora"])

    # Crear foreign key para asesor
    op.create_foreign_key(
        "fk_clientes_asesor_id",
        "clientes",
        ["asesor_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:

    # Eliminar foreign key
    op.drop_constraint("fk_clientes_asesor_id", "clientes", type_="foreignkey")

    # Eliminar índices
    op.drop_index("idx_clientes_dias_mora", "clientes")
    op.drop_index("idx_clientes_estado", "clientes")
    op.drop_index("idx_clientes_asesor_id", "clientes")
    op.drop_index("idx_clientes_modalidad_financiamiento", "clientes")
    op.drop_index("idx_clientes_concesionario", "clientes")
    op.drop_index("idx_clientes_modelo_vehiculo", "clientes")
    op.drop_index("idx_clientes_email", "clientes")
    op.drop_index("idx_clientes_telefono", "clientes")

    # Eliminar columnas
    op.drop_column("clientes", "saldo_pendiente_total")
    op.drop_column("clientes", "dias_mora")
    op.drop_column("clientes", "asesor_id")
    op.drop_column("clientes", "modalidad_financiamiento")
    op.drop_column("clientes", "numero_amortizaciones")
    op.drop_column("clientes", "fecha_entrega")
    op.drop_column("clientes", "cuota_inicial")
    op.drop_column("clientes", "total_financiamiento")
    op.drop_column("clientes", "concesionario")
    op.drop_column("clientes", "modelo_vehiculo")
