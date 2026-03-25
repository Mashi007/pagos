"""Tabla conversaciones_ai (entrenamiento / fine-tuning del chat).

Revision ID: 027_conversaciones_ai
Revises: 026_analistas_catalogo
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa


revision = "027_conversaciones_ai"
down_revision = "026_analistas_catalogo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversaciones_ai",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pregunta", sa.Text(), nullable=False),
        sa.Column("respuesta", sa.Text(), nullable=False),
        sa.Column("contexto_usado", sa.Text(), nullable=True),
        sa.Column("documentos_usados", sa.Text(), nullable=True),
        sa.Column("modelo_usado", sa.String(length=100), nullable=True),
        sa.Column("tokens_usados", sa.Integer(), nullable=True),
        sa.Column("tiempo_respuesta", sa.Integer(), nullable=True),
        sa.Column("calificacion", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversaciones_ai_creado_en",
        "conversaciones_ai",
        ["creado_en"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversaciones_ai_creado_en", table_name="conversaciones_ai")
    op.drop_table("conversaciones_ai")
