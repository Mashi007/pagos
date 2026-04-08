"""
Agregar índices para optimizar endpoints públicos (estado de cuenta, cobros).
Raíz del problema: Google bots + usuarios reales consultando la API generan picos de latencia.
Solución: índices compuestos en columnas frecuentemente consultadas.
"""
from alembic import op
import sqlalchemy as sa


revision = "033_optimize_public_api_indexes"
down_revision = "032_auditoria_cartera_revision_payload_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crear índices para optimizar queries públicas."""
    
    # Índice 1: clientes por cédula (validación rápida)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cliente_cedula ON clientes (cedula)
        WHERE cedula IS NOT NULL;
    """)
    
    # Índice 2: códigos de estado de cuenta activos (verificación rápida)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_estado_cuenta_codigo_cedula_activo 
        ON estado_cuenta_codigos (cedula_normalizada, usado, expira_en)
        WHERE usado = FALSE;
    """)
    
    # Índice 3: préstamos por cliente y estado (validación de reportes)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_prestamo_cliente_estado 
        ON prestamos (cliente_id, estado)
        WHERE estado = 'APROBADO';
    """)
    
    # Índice 4: pagos reportados por cédula y estado (búsquedas en panel)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pago_reportado_cedula_estado 
        ON pagos_reportados (tipo_cedula, numero_cedula, estado);
    """)
    
    # Índice 5: cuotas por prestamo (generación de PDF)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cuota_prestamo 
        ON cuotas (prestamo_id, numero_cuota)
        WHERE estado != 'CANCELADA';
    """)


def downgrade() -> None:
    """Eliminar índices."""
    op.execute("DROP INDEX IF EXISTS idx_cliente_cedula;")
    op.execute("DROP INDEX IF EXISTS idx_estado_cuenta_codigo_cedula_activo;")
    op.execute("DROP INDEX IF EXISTS idx_prestamo_cliente_estado;")
    op.execute("DROP INDEX IF EXISTS idx_pago_reportado_cedula_estado;")
    op.execute("DROP INDEX IF EXISTS idx_cuota_prestamo;")
