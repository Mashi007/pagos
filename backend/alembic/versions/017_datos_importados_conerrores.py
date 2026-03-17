"""Tabla datos_importados_conerrores para fallos de Importar reportados aprobados (Cobros).

Revision ID: 017_datos_importados_conerrores
Revises: 016_secuencia_ref_cobros
Create Date: 2026-03-16

Registros que no cumplen validadores al importar; se acumulan hasta descargar Excel; al descargar se vacía.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "017_datos_importados_conerrores"
down_revision = "016_secuencia_ref_cobros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "datos_importados_conerrores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cedula_cliente", sa.String(20), nullable=True),
        sa.Column("prestamo_id", sa.Integer(), nullable=True),
        sa.Column("fecha_pago", sa.DateTime(timezone=False), nullable=False),
        sa.Column("monto_pagado", sa.Numeric(14, 2), nullable=False),
        sa.Column("numero_documento", sa.String(100), nullable=True),
        sa.Column("estado", sa.String(30), server_default="PENDIENTE", nullable=True),
        sa.Column("referencia_pago", sa.String(100), server_default="", nullable=False),
        sa.Column("errores_descripcion", JSONB, nullable=True),
        sa.Column("observaciones", sa.String(255), nullable=True),
        sa.Column("fila_origen", sa.Integer(), nullable=True),
        sa.Column("referencia_interna", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_datos_importados_conerrores_cedula_cliente", "datos_importados_conerrores", ["cedula_cliente"])
    op.create_index("ix_datos_importados_conerrores_prestamo_id", "datos_importados_conerrores", ["prestamo_id"])


def downgrade() -> None:
    op.drop_index("ix_datos_importados_conerrores_prestamo_id", "datos_importados_conerrores")
    op.drop_index("ix_datos_importados_conerrores_cedula_cliente", "datos_importados_conerrores")
    op.drop_table("datos_importados_conerrores")
