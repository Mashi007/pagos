"""Add indexes for dashboard and reportes queries

Revision ID: 004_add_dashboard_indexes
Revises: 003_reporte_contable_cache
Create Date: 2026-02-21

Índices para optimizar consultas de:
- Dashboard (KPIs, gráficos, morosidad, cobranzas)
- Reportes (cartera, morosidad, pagos, vencimiento)

Columnas usadas en filtros y agregaciones:
- cuotas: prestamo_id, fecha_vencimiento, fecha_pago, cliente_id
- prestamos: cliente_id, estado, fecha_registro, analista, concesionario, modelo_vehiculo
- pagos: prestamo_id, fecha_pago
- clientes: estado (ya indexado)
"""
from alembic import op

revision = "004_add_dashboard_indexes"
down_revision = "003_reporte_contable_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cuotas: usadas en JOINs con prestamos + filtros por fecha_pago, fecha_vencimiento
    op.create_index(
        "idx_cuotas_prestamo_fecha_pago",
        "cuotas",
        ["prestamo_id", "fecha_pago"],
    )
    op.create_index(
        "idx_cuotas_prestamo_fecha_vencimiento",
        "cuotas",
        ["prestamo_id", "fecha_vencimiento"],
    )
    op.create_index("idx_cuotas_fecha_pago", "cuotas", ["fecha_pago"])
    op.create_index("idx_cuotas_fecha_vencimiento", "cuotas", ["fecha_vencimiento"])

    # Prestamos: join con clientes + filtros por estado, fecha_registro
    op.create_index(
        "idx_prestamos_cliente_estado",
        "prestamos",
        ["cliente_id", "estado"],
    )
    op.create_index("idx_prestamos_fecha_registro", "prestamos", ["fecha_registro"])
    op.create_index(
        "idx_prestamos_estado_fecha_registro",
        "prestamos",
        ["estado", "fecha_registro"],
    )

    # Pagos: filtros por fecha_pago, join con prestamos
    op.create_index("idx_pagos_fecha_pago", "pagos", ["fecha_pago"])
    op.create_index(
        "idx_pagos_prestamo_fecha",
        "pagos",
        ["prestamo_id", "fecha_pago"],
    )


def downgrade() -> None:
    op.drop_index("idx_pagos_prestamo_fecha", table_name="pagos")
    op.drop_index("idx_pagos_fecha_pago", table_name="pagos")
    op.drop_index("idx_prestamos_estado_fecha_registro", table_name="prestamos")
    op.drop_index("idx_prestamos_fecha_registro", table_name="prestamos")
    op.drop_index("idx_prestamos_cliente_estado", table_name="prestamos")
    op.drop_index("idx_cuotas_fecha_vencimiento", table_name="cuotas")
    op.drop_index("idx_cuotas_fecha_pago", table_name="cuotas")
    op.drop_index("idx_cuotas_prestamo_fecha_vencimiento", table_name="cuotas")
    op.drop_index("idx_cuotas_prestamo_fecha_pago", table_name="cuotas")
