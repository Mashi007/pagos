"""
Mejoras FASE 2: Optimización de vistas, triggers y caché
Fecha: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    """Crear vistas materializadas, triggers y tablas de caché."""
    
    # ============================================================================
    # 1. TRIGGER para actualizar clientes_retraso_snapshot
    # ============================================================================
    
    op.execute("""
        CREATE OR REPLACE FUNCTION actualizar_retraso_snapshot()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Refrescar vista materializada
            REFRESH MATERIALIZED VIEW CONCURRENTLY clientes_retrasados_mv;
            
            -- Actualizar tabla snapshot
            DELETE FROM clientes_retraso_snapshot;
            INSERT INTO clientes_retraso_snapshot (cliente_id, cedula, cuotas_retrasadas, updated_at)
            SELECT id, cedula, cuotas_retrasadas, NOW()
            FROM clientes_retrasados_mv;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Trigger cuando se crea/actualiza cuota
    op.execute("""
        CREATE TRIGGER trigger_actualizar_retraso_snapshot
        AFTER INSERT OR UPDATE ON cuotas
        FOR EACH ROW
        EXECUTE FUNCTION actualizar_retraso_snapshot();
    """)
    
    # ============================================================================
    # 2. VISTA MATERIALIZADA para KPIs (refresh cada 1 hora)
    # ============================================================================
    
    op.execute("""
        CREATE MATERIALIZED VIEW pagos_kpis_mv AS
        SELECT 
            COUNT(*) as total_pagos,
            COUNT(CASE WHEN estado='PAGADO' THEN 1 END) as pagos_completados,
            COUNT(CASE WHEN estado='PAGADO' THEN 1 END)::FLOAT / NULLIF(COUNT(*), 0) * 100 as porcentaje_pagado,
            SUM(CASE WHEN estado='PAGADO' THEN monto_pagado ELSE 0 END) as monto_total_pagado,
            AVG(CASE WHEN estado='PAGADO' AND fecha_conciliacion IS NOT NULL 
                THEN EXTRACT(DAY FROM fecha_conciliacion - fecha_pago) 
                ELSE NULL END) as dias_promedio_conciliacion,
            DATE_TRUNC('day', NOW()) as fecha_snapshot
        FROM pagos
        WHERE fecha_pago >= CURRENT_DATE - INTERVAL '30 days';
    """)
    
    # Índice en vista para búsquedas rápidas
    op.execute("""
        CREATE INDEX idx_pagos_kpis_mv_fecha 
        ON pagos_kpis_mv (fecha_snapshot DESC);
    """)
    
    # ============================================================================
    # 3. TABLA CACHÉ para adjuntos fijos cobranza
    # ============================================================================
    
    op.execute("""
        CREATE TABLE adjuntos_fijos_cache (
            caso VARCHAR(100) PRIMARY KEY,
            contenido BYTEA,
            nombre_archivo VARCHAR(255),
            tamaño_bytes BIGINT,
            hash_contenido VARCHAR(64),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            INDEX idx_adjuntos_fijos_cache_created 
                ON adjuntos_fijos_cache (created_at)
        );
        COMMENT ON TABLE adjuntos_fijos_cache IS 
            'Caché en BD para adjuntos fijos. TTL: 24h (eliminar vía job)';
    """)
    
    # ============================================================================
    # 4. TABLA CACHÉ para email config
    # ============================================================================
    
    op.execute("""
        CREATE TABLE email_config_cache (
            config_key VARCHAR(100) PRIMARY KEY,
            config_value JSONB,
            servicio VARCHAR(50),
            hash_value VARCHAR(64),
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '15 minutes'
        );
        COMMENT ON TABLE email_config_cache IS 
            'Caché en BD para configuración de email. TTL: 15 min';
    """)
    
    # Índice para búsquedas por servicio
    op.execute("""
        CREATE INDEX idx_email_config_cache_servicio 
        ON email_config_cache (servicio, created_at DESC);
    """)
    
    # ============================================================================
    # 5. FUNCIÓN para limpiar cachés expirados (job diario)
    # ============================================================================
    
    op.execute("""
        CREATE OR REPLACE FUNCTION limpiar_caches_expirados()
        RETURNS void AS $$
        BEGIN
            -- Limpiar email config cache expirada
            DELETE FROM email_config_cache 
            WHERE expires_at < NOW();
            
            -- Limpiar adjuntos fijos cache (> 24h)
            DELETE FROM adjuntos_fijos_cache 
            WHERE updated_at < NOW() - INTERVAL '24 hours';
            
            RAISE NOTICE 'Cachés expirados eliminados: %', NOW();
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # ============================================================================
    # 6. ÍNDICES ADICIONALES para optimización
    # ============================================================================
    
    # Índice para búsqueda rápida de pagos completados por fecha
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pagos_estado_fecha 
        ON pagos (estado, fecha_pago DESC) 
        WHERE estado = 'PAGADO';
    """)
    
    # Índice para búsqueda de cuotas vencidas
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cuotas_vencidas 
        ON cuotas (prestamo_id, fecha_pago) 
        WHERE fecha_pago < CURRENT_DATE AND estado != 'CANCELADA';
    """)
    
    # Índice en clientes para búsqueda por cédula + estado
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cliente_cedula_estado 
        ON clientes (cedula) 
        WHERE estado = 'ACTIVO';
    """)


def downgrade():
    """Remover vistas, triggers y tablas de caché."""
    
    # Remover triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_actualizar_retraso_snapshot ON cuotas;")
    
    # Remover funciones
    op.execute("DROP FUNCTION IF EXISTS actualizar_retraso_snapshot();")
    op.execute("DROP FUNCTION IF EXISTS limpiar_caches_expirados();")
    
    # Remover vistas
    op.execute("DROP MATERIALIZED VIEW IF EXISTS pagos_kpis_mv;")
    
    # Remover tablas
    op.execute("DROP TABLE IF EXISTS adjuntos_fijos_cache;")
    op.execute("DROP TABLE IF EXISTS email_config_cache;")
    
    # Remover índices adicionales
    op.execute("DROP INDEX IF EXISTS idx_pagos_estado_fecha;")
    op.execute("DROP INDEX IF EXISTS idx_cuotas_vencidas;")
    op.execute("DROP INDEX IF EXISTS idx_cliente_cedula_estado;")
