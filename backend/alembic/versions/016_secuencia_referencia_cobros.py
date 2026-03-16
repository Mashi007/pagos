"""Tabla secuencia_referencia_cobros para referencias RPC-YYYYMMDD-XXXXX.

Revision ID: 016_secuencia_ref_cobros
Revises: 015_gmail_temporal
Create Date: 2026-03-16

Evita InFailedSqlTransaction: la tabla debe existir antes de que el endpoint
enviar-reporte use _generar_referencia_interna (CREATE TABLE IF NOT EXISTS en runtime
puede fallar por permisos y deja la transacción abortada).
"""
from alembic import op
import sqlalchemy as sa

revision = "016_secuencia_ref_cobros"
down_revision = "015_gmail_temporal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS secuencia_referencia_cobros (
            fecha DATE PRIMARY KEY,
            siguiente INTEGER NOT NULL DEFAULT 1
        )
    """)
    op.execute("""
        COMMENT ON TABLE secuencia_referencia_cobros IS
        'Contador por día para referencia_interna de pagos_reportados (RPC-YYYYMMDD-XXXXX)'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS secuencia_referencia_cobros")
