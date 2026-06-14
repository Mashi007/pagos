"""finiquito_casos: permitir estado REVISION_CONTABLE en ck_finiquito_casos_estado.

Revision ID: 075_finiquito_estado_revision_contable
Revises: 074_revision_manual_conciliacion_reserva
Create Date: 2026-06-14
"""

from alembic import op

revision = "075_finiquito_estado_revision_contable"
down_revision = "074_revision_manual_conciliacion_reserva"
branch_labels = None
depends_on = None

_ESTADOS = (
    "'REVISION','ACEPTADO','REVISION_CONTABLE','RECHAZADO','EN_PROCESO','TERMINADO'"
)


def upgrade() -> None:
    op.drop_constraint("ck_finiquito_casos_estado", "finiquito_casos", type_="check")
    op.create_check_constraint(
        "ck_finiquito_casos_estado",
        "finiquito_casos",
        f"estado IN ({_ESTADOS})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_finiquito_casos_estado", "finiquito_casos", type_="check")
    op.create_check_constraint(
        "ck_finiquito_casos_estado",
        "finiquito_casos",
        "estado IN ('REVISION','ACEPTADO','RECHAZADO','EN_PROCESO','TERMINADO')",
    )
