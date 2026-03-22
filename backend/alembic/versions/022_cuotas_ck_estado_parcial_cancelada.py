"""Restaurar PARCIAL y CANCELADA en ck_cuotas_estado_valido

El script 019_add_rechazado_estado.sql redefinió el CHECK de cuotas incluyendo
RECHAZADO pero omitió PARCIAL y CANCELADA, que el backend usa al aplicar pagos
(FIFO) y en conciliación. Eso provoca IntegrityError al aprobar cobros.

Revision ID: 022_cuotas_ck_estado_parcial_cancelada
Revises: 021_pagos_pendiente_descargar
Create Date: 2026-03-22
"""

from alembic import op


revision = "022_cuotas_ck_estado_parcial_cancelada"
down_revision = "021_pagos_pendiente_descargar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_cuotas_estado_valido", "cuotas", type_="check")
    op.create_check_constraint(
        "ck_cuotas_estado_valido",
        "cuotas",
        "estado IN ("
        "'PENDIENTE', 'PAGADO', 'PAGO_ADELANTADO', 'VENCIDO', 'MORA', "
        "'PARCIAL', 'CANCELADA', 'RECHAZADO'"
        ")",
    )


def downgrade() -> None:
    # Vuelve al CHECK del script 019 (sin PARCIAL/CANCELADA; puede fallar si hay filas PARCIAL)
    op.drop_constraint("ck_cuotas_estado_valido", "cuotas", type_="check")
    op.create_check_constraint(
        "ck_cuotas_estado_valido",
        "cuotas",
        "estado IN ("
        "'PENDIENTE', 'PAGADO', 'PAGO_ADELANTADO', 'VENCIDO', 'MORA', 'RECHAZADO'"
        ")",
    )
