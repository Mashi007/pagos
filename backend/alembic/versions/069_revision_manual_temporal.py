"""Tabla temporal para Revisión Manual de Préstamos.

Almacena cambios en borrador antes de validar y confirmar.
Estados: borrador -> validado -> conciliado -> confirmado (o error)

Revision ID: 069_revision_manual_temporal
Revises: 068_cedulas_reportar_bs_fuente_tasa_cambio
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa


revision = "069_revision_manual_temporal"
down_revision = "068_cedulas_reportar_bs_fuente_tasa_cambio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revision_manual_prestamos_temp",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True, index=True),
        sa.Column("prestamo_id", sa.Integer(), nullable=False, index=True),
        sa.Column("cliente_datos_json", sa.Text(), nullable=True),
        sa.Column("prestamo_datos_json", sa.Text(), nullable=True),
        sa.Column("cuotas_datos_json", sa.Text(), nullable=True),
        sa.Column("pagos_datos_json", sa.Text(), nullable=True),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            index=True,
            server_default="'borrador'",
        ),
        sa.Column("validadores_resultado", sa.Text(), nullable=True),
        sa.Column("error_mensaje", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["prestamo_id"], ["prestamos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
    )

    op.create_index(
        "ix_revision_manual_temp_prestamo_usuario",
        "revision_manual_prestamos_temp",
        ["prestamo_id", "usuario_id"],
    )
    op.create_index(
        "ix_revision_manual_temp_estado", "revision_manual_prestamos_temp", ["estado"]
    )
    op.create_index(
        "ix_revision_manual_temp_creado",
        "revision_manual_prestamos_temp",
        ["creado_en"],
    )


def downgrade() -> None:
    op.drop_index("ix_revision_manual_temp_creado", table_name="revision_manual_prestamos_temp")
    op.drop_index(
        "ix_revision_manual_temp_estado", table_name="revision_manual_prestamos_temp"
    )
    op.drop_index(
        "ix_revision_manual_temp_prestamo_usuario",
        table_name="revision_manual_prestamos_temp",
    )
    op.drop_table("revision_manual_prestamos_temp")
