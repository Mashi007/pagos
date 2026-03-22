"""Columna prestamos.fecha_liquidado para emails diferidos (credito pagado).

Fecha calendario (America/Caracas) en que el prestamo paso a LIQUIDADO.
Se usa para enviar correos con PDF de estado de cuenta N dias despues.

Revision ID: 023_prestamos_fecha_liquidado
Revises: 022_cuotas_ck_estado_parcial_cancelada
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa


revision = "023_prestamos_fecha_liquidado"
down_revision = "022_cuotas_ck_estado_parcial_cancelada"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prestamos",
        sa.Column("fecha_liquidado", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_prestamos_fecha_liquidado",
        "prestamos",
        ["fecha_liquidado"],
        unique=False,
    )
    # Backfill: auditoria LIQUIDADO; si no hay fila, usar fecha_actualizacion::date
    op.execute(
        sa.text(
            """
            UPDATE prestamos p
            SET fecha_liquidado = COALESCE(
                (
                    SELECT MIN(a.fecha_cambio)::date
                    FROM auditoria_cambios_estado_prestamo a
                    WHERE a.prestamo_id = p.id
                      AND a.estado_nuevo = 'LIQUIDADO'
                ),
                p.fecha_actualizacion::date
            )
            WHERE p.estado = 'LIQUIDADO'
              AND p.fecha_liquidado IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_prestamos_fecha_liquidado", table_name="prestamos")
    op.drop_column("prestamos", "fecha_liquidado")
