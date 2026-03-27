"""prestamos: estado DESISTIMIENTO, columna fecha_desistimiento, CHECK ck_prestamos_estado_valido.

Revision ID: 029_prestamos_desistimiento
Revises: 028_envios_notificacion_metadata_tecnica
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "029_prestamos_desistimiento"
down_revision = "028_envios_notificacion_metadata_tecnica"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prestamos",
        sa.Column("fecha_desistimiento", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_prestamos_fecha_desistimiento",
        "prestamos",
        ["fecha_desistimiento"],
        unique=False,
    )
    op.execute(
        """
        ALTER TABLE public.prestamos
        DROP CONSTRAINT IF EXISTS ck_prestamos_estado_valido;
        """
    )
    op.execute(
        """
        ALTER TABLE public.prestamos
        ADD CONSTRAINT ck_prestamos_estado_valido
        CHECK (estado IN (
            'DRAFT', 'EN_REVISION', 'APROBADO', 'DESEMBOLSADO', 'EVALUADO',
            'RECHAZADO', 'LIQUIDADO', 'DESISTIMIENTO'
        ));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.prestamos
        DROP CONSTRAINT IF EXISTS ck_prestamos_estado_valido;
        """
    )
    op.execute(
        """
        ALTER TABLE public.prestamos
        ADD CONSTRAINT ck_prestamos_estado_valido
        CHECK (estado IN (
            'DRAFT', 'EN_REVISION', 'APROBADO', 'DESEMBOLSADO', 'EVALUADO',
            'RECHAZADO', 'LIQUIDADO'
        ));
        """
    )
    op.drop_index("ix_prestamos_fecha_desistimiento", table_name="prestamos")
    op.drop_column("prestamos", "fecha_desistimiento")
