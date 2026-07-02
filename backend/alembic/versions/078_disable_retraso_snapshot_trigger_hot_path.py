"""Disable retraso snapshot trigger on cuotas hot path.

Revision ID: 078_disable_retraso_snapshot_trigger_hot_path
Revises: 077_pagos_reportados_fuente_tasa_cambio
Create Date: 2026-07-02

El trigger `trigger_actualizar_retraso_snapshot` refresca la vista materializada
`clientes_retrasados_mv` en cada INSERT/UPDATE de `cuotas`. En producción esto
está provocando timeouts en el flujo de aplicar pagos (`UPDATE cuotas ...`)
porque el `REFRESH MATERIALIZED VIEW` corre dentro de la misma transacción.

Como no hay consumidores runtime en `backend/app` que dependan de refresco
sincrónico inmediato, desactivamos el trigger para sacar ese costo del hot path.
La infraestructura (vista, snapshot y función) se conserva para un refresco
manual o programado fuera de la transacción de pagos.
"""

from alembic import op


revision = "078_disable_retraso_snapshot_trigger_hot_path"
down_revision = "077_pagos_reportados_fuente_tasa_cambio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_actualizar_retraso_snapshot ON cuotas;")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION actualizar_retraso_snapshot()
        RETURNS TRIGGER AS $$
        BEGIN
            -- No-op: el refresh síncrono de la MV sale del hot path de pagos/cuotas.
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION actualizar_retraso_snapshot()
        RETURNS TRIGGER AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW clientes_retrasados_mv;

            DELETE FROM clientes_retraso_snapshot;
            INSERT INTO clientes_retraso_snapshot
                (cliente_id, cedula, cuotas_retrasadas, updated_at)
            SELECT id, cedula, cuotas_retrasadas, NOW()
            FROM clientes_retrasados_mv;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trigger_actualizar_retraso_snapshot
        AFTER INSERT OR UPDATE ON cuotas
        FOR EACH STATEMENT
        EXECUTE FUNCTION actualizar_retraso_snapshot();
        """
    )
