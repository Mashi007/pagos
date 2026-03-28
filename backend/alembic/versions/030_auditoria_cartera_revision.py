"""Tabla auditoria_cartera_revision (bitacora revision alertas cartera).

Revision ID: 030_auditoria_cartera_revision
Revises: 029_prestamos_desistimiento
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "030_auditoria_cartera_revision"
down_revision = "029_prestamos_desistimiento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auditoria_cartera_revision",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prestamo_id", sa.Integer(), nullable=False),
        sa.Column("codigo_control", sa.String(length=80), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False, server_default="MARCAR_OK"),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["prestamo_id"], ["prestamos.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auditoria_cartera_revision_prestamo_id",
        "auditoria_cartera_revision",
        ["prestamo_id"],
        unique=False,
    )
    op.create_index(
        "ix_auditoria_cartera_revision_usuario_id",
        "auditoria_cartera_revision",
        ["usuario_id"],
        unique=False,
    )
    op.create_index(
        "ix_auditoria_cartera_revision_creado_en",
        "auditoria_cartera_revision",
        ["creado_en"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_auditoria_cartera_revision_creado_en", table_name="auditoria_cartera_revision")
    op.drop_index("ix_auditoria_cartera_revision_usuario_id", table_name="auditoria_cartera_revision")
    op.drop_index("ix_auditoria_cartera_revision_prestamo_id", table_name="auditoria_cartera_revision")
    op.drop_table("auditoria_cartera_revision")
