"""Fix materialized views - create unique indices for CONCURRENT REFRESH

Revision ID: 035_fix_mv_indices
Revises: 034_fase2_vistas_triggers_cache
Create Date: 2026-03-30 10:00:00.000000

PostgreSQL requirement: Materialized views must have a unique index without WHERE clause
to support REFRESH MATERIALIZED VIEW CONCURRENTLY.

Error fixed: 
  psycopg2.errors.ObjectNotInPrerequisiteState: 
  cannot refresh materialized view "public.clientes_retrasados_mv" concurrently
  HINT: Create a unique index with no WHERE clause on one or more columns

This was blocking the trigger `actualizar_retraso_snapshot()` from working.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '035_fix_mv_indices'
down_revision = '034_fase2_vistas_triggers_cache'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create unique index on clientes_retrasados_mv
    # This allows REFRESH MATERIALIZED VIEW CONCURRENTLY
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_clientes_retrasados_mv_id 
        ON clientes_retrasados_mv (id)
    """)
    
    # Create unique index on pagos_kpis_mv
    # This allows REFRESH MATERIALIZED VIEW CONCURRENTLY
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pagos_kpis_mv_fecha
        ON pagos_kpis_mv (fecha_snapshot)
    """)


def downgrade() -> None:
    # Remove the indices if downgrading
    op.execute("""
        DROP INDEX IF EXISTS idx_clientes_retrasados_mv_id
    """)
    
    op.execute("""
        DROP INDEX IF EXISTS idx_pagos_kpis_mv_fecha
    """)
