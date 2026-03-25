"""Finiquito: EN_PROCESO, TERMINADO, contacto_para_siguientes, auditoria area de trabajo.

Revision ID: 025_finiquito_area_trabajo
Revises: 024_finiquito_tablas
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa


revision = "025_finiquito_area_trabajo"
down_revision = "024_finiquito_tablas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_finiquito_casos_estado", "finiquito_casos", type_="check")
    op.create_check_constraint(
        "ck_finiquito_casos_estado",
        "finiquito_casos",
        "estado IN ('REVISION','ACEPTADO','RECHAZADO','EN_PROCESO','TERMINADO')",
    )
    op.add_column(
        "finiquito_casos",
        sa.Column("contacto_para_siguientes", sa.Boolean(), nullable=True),
    )
    op.create_table(
        "finiquito_area_trabajo_auditoria",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "caso_id",
            sa.Integer(),
            sa.ForeignKey("finiquito_casos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("accion", sa.String(length=32), nullable=False),
        sa.Column("estado_anterior", sa.String(length=20), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=20), nullable=False),
        sa.Column("contacto_para_siguientes", sa.Boolean(), nullable=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finiquito_at_aud_caso_id",
        "finiquito_area_trabajo_auditoria",
        ["caso_id"],
        unique=False,
    )
    op.create_index(
        "ix_finiquito_at_aud_creado_en",
        "finiquito_area_trabajo_auditoria",
        ["creado_en"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_finiquito_at_aud_creado_en", table_name="finiquito_area_trabajo_auditoria")
    op.drop_index("ix_finiquito_at_aud_caso_id", table_name="finiquito_area_trabajo_auditoria")
    op.drop_table("finiquito_area_trabajo_auditoria")
    op.drop_column("finiquito_casos", "contacto_para_siguientes")
    op.drop_constraint("ck_finiquito_casos_estado", "finiquito_casos", type_="check")
    op.create_check_constraint(
        "ck_finiquito_casos_estado",
        "finiquito_casos",
        "estado IN ('REVISION','ACEPTADO','RECHAZADO')",
    )
