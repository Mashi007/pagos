"""Trigger clientes_retrasados: REFRESH MV sin CONCURRENTLY y por sentencia.

Revision ID: 048_fix_retraso_snapshot_trigger_refresh_in_transaction
Revises: 047_auditoria_control5_sufijo_prefijo_ap
Create Date: 2026-04-04

PostgreSQL no permite REFRESH MATERIALIZED VIEW CONCURRENTLY dentro de un
bloque de transacción. El trigger en cuotas (FASE 2) ejecutaba CONCURRENTLY
en cada fila actualizada; al finalizar revisión manual con saldo cero se
actualizan muchas cuotas en la misma transacción y el commit fallaba con 500.

- REFRESH sin CONCURRENTLY es válido dentro de la transacción (bloqueo breve
  sobre la vista).
- FOR EACH STATEMENT reduce refrescos cuando un UPDATE toca varias filas.

"""
from alembic import op


revision = "048_fix_retraso_snapshot_trigger_refresh_in_transaction"
down_revision = "047_auditoria_control5_sufijo_prefijo_ap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_actualizar_retraso_snapshot ON cuotas;")
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


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_actualizar_retraso_snapshot ON cuotas;")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION actualizar_retraso_snapshot()
        RETURNS TRIGGER AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY clientes_retrasados_mv;

            DELETE FROM clientes_retraso_snapshot;
            INSERT INTO clientes_retraso_snapshot
                (cliente_id, cedula, cuotas_retrasadas, updated_at)
            SELECT id, cedula, cuotas_retrasadas, NOW()
            FROM clientes_retrasados_mv;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trigger_actualizar_retraso_snapshot
        AFTER INSERT OR UPDATE ON cuotas
        FOR EACH ROW
        EXECUTE FUNCTION actualizar_retraso_snapshot();
        """
    )
