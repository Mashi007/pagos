"""revision_manual: solicitudes de reapertura (operario -> admin).

Revision ID: 051_revision_manual_solicitudes_reapertura
Revises: 050_prestamos_finiquito_tramite_fecha_limite
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "051_revision_manual_solicitudes_reapertura"
down_revision = "050_prestamos_finiquito_tramite_fecha_limite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revision_manual_solicitudes_reapertura",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prestamo_id", sa.Integer(), nullable=False),
        sa.Column("solicitante_usuario_id", sa.Integer(), nullable=True),
        sa.Column("solicitante_email", sa.String(length=255), nullable=True),
        sa.Column("mensaje", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=20), server_default=sa.text("'pendiente'"), nullable=False),
        sa.Column("resuelto_por_usuario_id", sa.Integer(), nullable=True),
        sa.Column("nota_resolucion", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("resuelto_en", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["prestamo_id"], ["prestamos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resuelto_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["solicitante_usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_revision_manual_sol_reap_prestamo_id",
        "revision_manual_solicitudes_reapertura",
        ["prestamo_id"],
        unique=False,
    )
    op.create_index(
        "ix_revision_manual_sol_reap_solicitante_usuario_id",
        "revision_manual_solicitudes_reapertura",
        ["solicitante_usuario_id"],
        unique=False,
    )
    op.create_index(
        "ix_revision_manual_sol_reap_estado",
        "revision_manual_solicitudes_reapertura",
        ["estado"],
        unique=False,
    )
    op.create_index(
        "uq_rm_sol_reap_un_pendiente_por_prestamo",
        "revision_manual_solicitudes_reapertura",
        ["prestamo_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'pendiente'"),
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_rm_sol_reap_un_pendiente_por_prestamo")
    op.drop_index("ix_revision_manual_sol_reap_estado", table_name="revision_manual_solicitudes_reapertura")
    op.drop_index(
        "ix_revision_manual_sol_reap_solicitante_usuario_id",
        table_name="revision_manual_solicitudes_reapertura",
    )
    op.drop_index("ix_revision_manual_sol_reap_prestamo_id", table_name="revision_manual_solicitudes_reapertura")
    op.drop_table("revision_manual_solicitudes_reapertura")
