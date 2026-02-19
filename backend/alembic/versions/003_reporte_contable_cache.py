"""Create reporte_contable_cache table

Revision ID: 003_reporte_contable_cache
Revises: 002_add_referential_integrity
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa

revision = "003_reporte_contable_cache"
down_revision = "002_add_referential_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reporte_contable_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cuota_id", sa.Integer(), nullable=False),
        sa.Column("cedula", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("tipo_documento", sa.String(50), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("fecha_pago", sa.Date(), nullable=False),
        sa.Column("importe_md", sa.Numeric(14, 2), nullable=False),
        sa.Column("moneda_documento", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("tasa", sa.Numeric(14, 4), nullable=False),
        sa.Column("importe_ml", sa.Numeric(14, 2), nullable=False),
        sa.Column("moneda_local", sa.String(10), nullable=False, server_default="Bs."),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cuota_id"], ["cuotas.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("cuota_id", name="uq_reporte_contable_cache_cuota_id"),
    )
    op.create_index("idx_reporte_contable_cache_cuota", "reporte_contable_cache", ["cuota_id"])
    op.create_index("idx_reporte_contable_cache_cedula", "reporte_contable_cache", ["cedula"])
    op.create_index("idx_reporte_contable_cache_fecha", "reporte_contable_cache", ["fecha_pago"])
    op.create_index("idx_reporte_contable_cache_fecha_cedula", "reporte_contable_cache", ["fecha_pago", "cedula"])


def downgrade() -> None:
    op.drop_index("idx_reporte_contable_cache_fecha_cedula", table_name="reporte_contable_cache")
    op.drop_index("idx_reporte_contable_cache_fecha", table_name="reporte_contable_cache")
    op.drop_index("idx_reporte_contable_cache_cedula", table_name="reporte_contable_cache")
    op.drop_index("idx_reporte_contable_cache_cuota", table_name="reporte_contable_cache")
    op.drop_table("reporte_contable_cache")
