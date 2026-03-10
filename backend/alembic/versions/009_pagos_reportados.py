"""Tablas pagos_reportados y pagos_reportados_historial (módulo Cobros)

Revision ID: 009_pagos_reportados
Revises: 008_drive_email_link
Create Date: 2026-03

Formulario público de reporte de pago + administración Cobros.
"""
from alembic import op
import sqlalchemy as sa


revision = "009_pagos_reportados"
down_revision = "008_drive_email_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pagos_reportados",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("referencia_interna", sa.String(32), nullable=False),
        sa.Column("nombres", sa.String(200), nullable=False),
        sa.Column("apellidos", sa.String(200), nullable=False),
        sa.Column("tipo_cedula", sa.String(2), nullable=False),
        sa.Column("numero_cedula", sa.String(13), nullable=False),
        sa.Column("fecha_pago", sa.Date(), nullable=False),
        sa.Column("institucion_financiera", sa.String(100), nullable=False),
        sa.Column("numero_operacion", sa.String(100), nullable=False),
        sa.Column("monto", sa.Numeric(15, 2), nullable=False),
        sa.Column("moneda", sa.String(10), nullable=False, server_default="'BS'"),
        sa.Column("ruta_comprobante", sa.String(512), nullable=False),
        sa.Column("observacion", sa.Text(), nullable=True),
        sa.Column("correo_enviado_a", sa.String(255), nullable=True),
        sa.Column("ruta_recibo_pdf", sa.String(512), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="'pendiente'"),
        sa.Column("motivo_rechazo", sa.Text(), nullable=True),
        sa.Column("usuario_gestion_id", sa.Integer(), nullable=True),
        sa.Column("gemini_coincide_exacto", sa.String(10), nullable=True),
        sa.Column("gemini_comentario", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referencia_interna", name="uq_pagos_reportados_referencia"),
        sa.ForeignKeyConstraint(["usuario_gestion_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_pagos_reportados_referencia_interna", "pagos_reportados", ["referencia_interna"], unique=True)
    op.create_index("ix_pagos_reportados_numero_cedula", "pagos_reportados", ["numero_cedula"])
    op.create_index("ix_pagos_reportados_estado", "pagos_reportados", ["estado"])
    op.create_index("ix_pagos_reportados_created_at", "pagos_reportados", ["created_at"])

    op.create_table(
        "pagos_reportados_historial",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pago_reportado_id", sa.Integer(), nullable=False),
        sa.Column("estado_anterior", sa.String(20), nullable=True),
        sa.Column("estado_nuevo", sa.String(20), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("usuario_email", sa.String(255), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pago_reportado_id"], ["pagos_reportados.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_pagos_reportados_historial_pago_id", "pagos_reportados_historial", ["pago_reportado_id"])


def downgrade() -> None:
    op.drop_table("pagos_reportados_historial")
    op.drop_table("pagos_reportados")
