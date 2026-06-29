"""pagos_reportados: columna fuente_tasa_cambio (bcv|euro|binance).

El modelo y crear_pago_reportado_con_referencia_o_retry ya persisten este campo;
existia solo en backend/scripts/sql/20260422_tasas_multifuente_pagos_reportados.sql
(sin revision Alembic). Sin la columna, POST enviar-reporte falla al INSERT.

Revision ID: 077_pagos_reportados_fuente_tasa_cambio
Revises: 076_prestamos_gestion_finiquito_fases_intermedias
Create Date: 2026-06-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "077_pagos_reportados_fuente_tasa_cambio"
down_revision = "076_prestamos_gestion_finiquito_fases_intermedias"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("pagos_reportados")}
    if "fuente_tasa_cambio" in cols:
        return
    op.add_column(
        "pagos_reportados",
        sa.Column(
            "fuente_tasa_cambio",
            sa.String(length=16),
            nullable=True,
            server_default=sa.text("'euro'"),
        ),
    )
    op.execute(
        """
        UPDATE pagos_reportados
        SET fuente_tasa_cambio = 'euro'
        WHERE fuente_tasa_cambio IS NULL
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("pagos_reportados")}
    if "fuente_tasa_cambio" not in cols:
        return
    op.drop_column("pagos_reportados", "fuente_tasa_cambio")
