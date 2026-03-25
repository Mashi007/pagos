"""envios_notificacion: mensaje_html, mensaje_texto, comprobante_pdf; tabla adjuntos

Revision ID: 027_envios_notificacion_snapshot
Revises: 026_analistas_catalogo
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "027_envios_notificacion_snapshot"
down_revision = "026_analistas_catalogo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("envios_notificacion", sa.Column("mensaje_html", sa.Text(), nullable=True))
    op.add_column("envios_notificacion", sa.Column("mensaje_texto", sa.Text(), nullable=True))
    op.add_column("envios_notificacion", sa.Column("comprobante_pdf", sa.LargeBinary(), nullable=True))
    op.create_table(
        "envios_notificacion_adjuntos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("envio_notificacion_id", sa.Integer(), nullable=False),
        sa.Column("nombre_archivo", sa.String(length=255), nullable=False),
        sa.Column("contenido", sa.LargeBinary(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["envio_notificacion_id"],
            ["envios_notificacion.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_envios_notif_adjuntos_envio_id",
        "envios_notificacion_adjuntos",
        ["envio_notificacion_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_envios_notif_adjuntos_envio_id", table_name="envios_notificacion_adjuntos")
    op.drop_table("envios_notificacion_adjuntos")
    op.drop_column("envios_notificacion", "comprobante_pdf")
    op.drop_column("envios_notificacion", "mensaje_texto")
    op.drop_column("envios_notificacion", "mensaje_html")
