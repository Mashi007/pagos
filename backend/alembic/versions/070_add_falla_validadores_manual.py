"""Columna pre-calculada falla_validadores_manual en pagos_reportados.

Permite filtrar a nivel SQL los reportes que requieren revision manual,
eliminando el barrido completo en Python que causaba >25 s en listado-y-kpis.

Backfill conservador: gemini_coincide_exacto='true'/'1' -> false (pasa validadores);
'error'/NULL/otros -> true (necesita revision). Estados terminales -> false.
El recalculo preciso ocurre en cada escritura y en el backfill progresivo del endpoint.

Revision ID: 070_add_falla_validadores_manual
Revises: 069_revision_manual_temporal
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa


revision = "070_add_falla_validadores_manual"
down_revision = "069_revision_manual_temporal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pagos_reportados",
        sa.Column("falla_validadores_manual", sa.Boolean(), nullable=True),
    )

    op.create_index(
        "ix_pagos_reportados_falla_val_estado",
        "pagos_reportados",
        ["falla_validadores_manual", "estado", "created_at"],
    )

    op.execute("""
        UPDATE pagos_reportados
        SET falla_validadores_manual = CASE
            WHEN estado IN ('importado', 'rechazado', 'eliminado_duplicado')
                THEN false
            WHEN LOWER(TRIM(COALESCE(gemini_coincide_exacto, ''))) IN ('true', '1')
                THEN false
            ELSE true
        END
    """)


def downgrade() -> None:
    op.drop_index("ix_pagos_reportados_falla_val_estado", table_name="pagos_reportados")
    op.drop_column("pagos_reportados", "falla_validadores_manual")
