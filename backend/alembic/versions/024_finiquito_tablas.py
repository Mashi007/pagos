"""Tablas Finiquito: casos materializados, historial de estados, acceso publico OTP.

Revision ID: 024_finiquito_tablas
Revises: 023_prestamos_fecha_liquidado
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa


revision = "024_finiquito_tablas"
down_revision = "023_prestamos_fecha_liquidado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finiquito_usuario_acceso",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cedula", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        "ix_finiquito_usuario_acceso_cedula",
        "finiquito_usuario_acceso",
        ["cedula"],
        unique=True,
    )
    op.create_index(
        "ix_finiquito_usuario_acceso_email",
        "finiquito_usuario_acceso",
        ["email"],
        unique=True,
    )

    op.create_table(
        "finiquito_login_codigos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "finiquito_usuario_id",
            sa.Integer(),
            sa.ForeignKey("finiquito_usuario_acceso.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("codigo", sa.String(length=10), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=False), nullable=False),
        sa.Column(
            "usado",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("creado_en", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finiquito_login_codigos_usuario",
        "finiquito_login_codigos",
        ["finiquito_usuario_id"],
        unique=False,
    )

    op.create_table(
        "finiquito_casos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "prestamo_id",
            sa.Integer(),
            sa.ForeignKey("prestamos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cliente_id",
            sa.Integer(),
            sa.ForeignKey("clientes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("cedula", sa.String(length=20), nullable=False),
        sa.Column("total_financiamiento", sa.Numeric(14, 2), nullable=False),
        sa.Column("sum_total_pagado", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'REVISION'"),
        ),
        sa.Column(
            "ultimo_refresh_utc",
            sa.DateTime(timezone=False),
            nullable=True,
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "estado IN ('REVISION','ACEPTADO','RECHAZADO')",
            name="ck_finiquito_casos_estado",
        ),
    )
    op.create_index(
        "ix_finiquito_casos_prestamo_id",
        "finiquito_casos",
        ["prestamo_id"],
        unique=True,
    )
    op.create_index(
        "ix_finiquito_casos_cliente_id",
        "finiquito_casos",
        ["cliente_id"],
        unique=False,
    )
    op.create_index(
        "ix_finiquito_casos_cedula",
        "finiquito_casos",
        ["cedula"],
        unique=False,
    )
    op.create_index(
        "ix_finiquito_casos_estado",
        "finiquito_casos",
        ["estado"],
        unique=False,
    )

    op.create_table(
        "finiquito_estado_historial",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "caso_id",
            sa.Integer(),
            sa.ForeignKey("finiquito_casos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("estado_anterior", sa.String(length=20), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=20), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "finiquito_usuario_id",
            sa.Integer(),
            sa.ForeignKey("finiquito_usuario_acceso.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_tipo", sa.String(length=20), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finiquito_estado_historial_caso_id",
        "finiquito_estado_historial",
        ["caso_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_finiquito_estado_historial_caso_id", table_name="finiquito_estado_historial")
    op.drop_table("finiquito_estado_historial")
    op.drop_index("ix_finiquito_casos_estado", table_name="finiquito_casos")
    op.drop_index("ix_finiquito_casos_cedula", table_name="finiquito_casos")
    op.drop_index("ix_finiquito_casos_cliente_id", table_name="finiquito_casos")
    op.drop_index("ix_finiquito_casos_prestamo_id", table_name="finiquito_casos")
    op.drop_table("finiquito_casos")
    op.drop_index("ix_finiquito_login_codigos_usuario", table_name="finiquito_login_codigos")
    op.drop_table("finiquito_login_codigos")
    op.drop_index("ix_finiquito_usuario_acceso_email", table_name="finiquito_usuario_acceso")
    op.drop_index("ix_finiquito_usuario_acceso_cedula", table_name="finiquito_usuario_acceso")
    op.drop_table("finiquito_usuario_acceso")
