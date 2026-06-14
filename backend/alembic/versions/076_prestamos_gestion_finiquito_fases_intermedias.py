"""prestamos: backfill estado_gestion_finiquito para ACEPTADO y REVISION_CONTABLE.

Revision ID: 076_prestamos_gestion_finiquito_fases_intermedias
Revises: 075_finiquito_estado_revision_contable
Create Date: 2026-06-14
"""

from alembic import op

revision = "076_prestamos_gestion_finiquito_fases_intermedias"
down_revision = "075_finiquito_estado_revision_contable"
branch_labels = None
depends_on = None

_ESTADOS_REFLEJADOS = (
    "'REVISION','ACEPTADO','REVISION_CONTABLE','EN_PROCESO','TERMINADO'"
)


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE prestamos p
        SET estado_gestion_finiquito = UPPER(TRIM(c.estado))
        FROM finiquito_casos c
        WHERE c.prestamo_id = p.id
          AND UPPER(TRIM(c.estado)) IN ({_ESTADOS_REFLEJADOS});
        """
    )
    op.execute(
        """
        UPDATE prestamos
        SET estado_gestion_finiquito = 'REVISION'
        WHERE UPPER(TRIM(COALESCE(estado_gestion_finiquito, ''))) = 'ANTIGUO';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE prestamos p
        SET estado_gestion_finiquito = NULL
        FROM finiquito_casos c
        WHERE c.prestamo_id = p.id
          AND UPPER(TRIM(c.estado)) IN ('ACEPTADO', 'REVISION_CONTABLE')
          AND UPPER(TRIM(COALESCE(p.estado_gestion_finiquito, ''))) = UPPER(TRIM(c.estado));
        """
    )
