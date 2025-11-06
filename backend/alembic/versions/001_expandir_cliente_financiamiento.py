"""expandir cliente financiamiento

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
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if "clientes" not in inspector.get_table_names():
        print("⚠️ Tabla 'clientes' no existe, saltando migración")
        return
    
    # Verificar columnas existentes
    columns = [col["name"] for col in inspector.get_columns("clientes")]
    
    # Agregar columnas solo si no existen
    if "modelo_vehiculo" not in columns:
        op.add_column("clientes", sa.Column("modelo_vehiculo", sa.String(100), nullable=True))
    if "concesionario" not in columns:
        op.add_column("clientes", sa.Column("concesionario", sa.String(100), nullable=True))
    if "total_financiamiento" not in columns:
        op.add_column("clientes", sa.Column("total_financiamiento", sa.Numeric(12, 2), nullable=True))
    if "cuota_inicial" not in columns:
        op.add_column("clientes", sa.Column("cuota_inicial", sa.Numeric(12, 2), server_default="0.00"))
    if "fecha_entrega" not in columns:
        op.add_column("clientes", sa.Column("fecha_entrega", sa.Date(), nullable=True))
    if "numero_amortizaciones" not in columns:
        op.add_column("clientes", sa.Column("numero_amortizaciones", sa.Integer(), nullable=True))
    if "modalidad_financiamiento" not in columns:
        op.add_column("clientes", sa.Column("modalidad_financiamiento", sa.String(20), server_default="MENSUAL"))
    if "asesor_id" not in columns:
        op.add_column("clientes", sa.Column("asesor_id", sa.Integer(), nullable=True))
    if "dias_mora" not in columns:
        op.add_column("clientes", sa.Column("dias_mora", sa.Integer(), server_default="0"))
    if "saldo_pendiente_total" not in columns:
        op.add_column("clientes", sa.Column("saldo_pendiente_total", sa.Numeric(12, 2), server_default="0.00"))

    # Verificar índices existentes
    indexes = [idx["name"] for idx in inspector.get_indexes("clientes")]
    
    # Crear índices solo si no existen
    if "idx_clientes_telefono" not in indexes:
        op.create_index("idx_clientes_telefono", "clientes", ["telefono"])
    if "idx_clientes_email" not in indexes:
        op.create_index("idx_clientes_email", "clientes", ["email"])
    if "idx_clientes_modelo_vehiculo" not in indexes:
        op.create_index("idx_clientes_modelo_vehiculo", "clientes", ["modelo_vehiculo"])
    if "idx_clientes_concesionario" not in indexes:
        op.create_index("idx_clientes_concesionario", "clientes", ["concesionario"])
    if "idx_clientes_modalidad_financiamiento" not in indexes:
        op.create_index("idx_clientes_modalidad_financiamiento", "clientes", ["modalidad_financiamiento"])
    if "idx_clientes_asesor_id" not in indexes:
        op.create_index("idx_clientes_asesor_id", "clientes", ["asesor_id"])
    if "idx_clientes_estado" not in indexes:
        op.create_index("idx_clientes_estado", "clientes", ["estado"])
    if "idx_clientes_dias_mora" not in indexes:
        op.create_index("idx_clientes_dias_mora", "clientes", ["dias_mora"])

    # Verificar foreign keys existentes
    foreign_keys = [fk["name"] for fk in inspector.get_foreign_keys("clientes")]
    
    # Crear foreign key solo si no existe
    if "fk_clientes_asesor_id" not in foreign_keys:
        op.create_foreign_key("fk_clientes_asesor_id", "clientes", "users", ["asesor_id"], ["id"])


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
