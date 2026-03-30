-- ============================================================================
-- MIGRACIÓN FASE 2: Vistas materializadas, triggers y cachés
-- Fecha: 2026-03-30
-- Propósito: Reducir latencia 74-92% en endpoints costosos
-- ============================================================================

-- 1. VISTA MATERIALIZADA: clientes_retrasados_mv
-- ============================================================================
CREATE MATERIALIZED VIEW clientes_retrasados_mv AS
SELECT 
    c.id, 
    c.cedula, 
    COUNT(*) as cuotas_retrasadas,
    SUM(cu.monto_cuota) as monto_total_retrasado,
    MIN(cu.fecha_vencimiento) as fecha_mas_antigua,
    MAX(cu.fecha_vencimiento) as fecha_mas_reciente
FROM clientes c
JOIN prestamos p ON c.id = p.cliente_id
JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE cu.fecha_vencimiento < CURRENT_DATE
  AND cu.estado != 'CANCELADA'
GROUP BY c.id, c.cedula;

CREATE INDEX idx_clientes_retrasados_mv_cedula 
ON clientes_retrasados_mv (cedula);

-- 2. TABLA SNAPSHOT: clientes_retraso_snapshot
-- ============================================================================
CREATE TABLE clientes_retraso_snapshot (
    cliente_id INT PRIMARY KEY,
    cedula VARCHAR(50),
    cuotas_retrasadas INT,
    monto_total_retrasado DECIMAL(15, 2),
    fecha_mas_antigua DATE,
    fecha_mas_reciente DATE,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_clientes_retraso_snapshot_cedula 
ON clientes_retraso_snapshot (cedula);

CREATE INDEX idx_clientes_retraso_snapshot_updated 
ON clientes_retraso_snapshot (updated_at DESC);

-- 3. VISTA MATERIALIZADA: pagos_kpis_mv
-- ============================================================================
CREATE MATERIALIZED VIEW pagos_kpis_mv AS
SELECT 
    COUNT(*) as total_pagos,
    COUNT(CASE WHEN estado='PAGADO' THEN 1 END) as pagos_completados,
    ROUND(
        COUNT(CASE WHEN estado='PAGADO' THEN 1 END)::FLOAT / NULLIF(COUNT(*), 0) * 100, 
        2
    ) as porcentaje_pagado,
    SUM(CASE WHEN estado='PAGADO' THEN monto_pagado ELSE 0 END) as monto_total_pagado,
    ROUND(
        AVG(CASE WHEN estado='PAGADO' AND fecha_conciliacion IS NOT NULL 
            THEN EXTRACT(DAY FROM fecha_conciliacion - fecha_pago) 
            ELSE NULL END),
        2
    ) as dias_promedio_conciliacion,
    DATE_TRUNC('day', NOW()) as fecha_snapshot
FROM pagos
WHERE fecha_pago >= CURRENT_DATE - INTERVAL '30 days';

CREATE INDEX idx_pagos_kpis_mv_fecha 
ON pagos_kpis_mv (fecha_snapshot DESC);

-- 4. TABLA CACHÉ: adjuntos_fijos_cache
-- ============================================================================
CREATE TABLE adjuntos_fijos_cache (
    id SERIAL PRIMARY KEY,
    caso VARCHAR(100) NOT NULL UNIQUE,
    contenido BYTEA NOT NULL,
    nombre_archivo VARCHAR(255),
    tamaño_bytes BIGINT,
    hash_contenido VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_adjuntos_fijos_cache_caso 
ON adjuntos_fijos_cache (caso);

CREATE INDEX idx_adjuntos_fijos_cache_created 
ON adjuntos_fijos_cache (created_at DESC);

-- 5. TABLA CACHÉ: email_config_cache
-- ============================================================================
CREATE TABLE email_config_cache (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB,
    servicio VARCHAR(50),
    hash_value VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '15 minutes'
);

CREATE INDEX idx_email_config_cache_key 
ON email_config_cache (config_key);

CREATE INDEX idx_email_config_cache_servicio 
ON email_config_cache (servicio, created_at DESC);

CREATE INDEX idx_email_config_cache_expires 
ON email_config_cache (expires_at);

-- 6. FUNCIÓN: actualizar_retraso_snapshot
-- ============================================================================
CREATE OR REPLACE FUNCTION actualizar_retraso_snapshot()
RETURNS TRIGGER AS $$
BEGIN
    -- Refrescar vista materializada (sin bloqueos)
    REFRESH MATERIALIZED VIEW CONCURRENTLY clientes_retrasados_mv;
    
    -- Actualizar tabla snapshot
    DELETE FROM clientes_retraso_snapshot;
    INSERT INTO clientes_retraso_snapshot 
        (cliente_id, cedula, cuotas_retrasadas, monto_total_retrasado, 
         fecha_mas_antigua, fecha_mas_reciente, updated_at)
    SELECT 
        id, cedula, cuotas_retrasadas, monto_total_retrasado,
        fecha_mas_antigua, fecha_mas_reciente, NOW()
    FROM clientes_retrasados_mv;
    
    RAISE NOTICE 'snapshot actualizado: % clientes retrasados', 
        (SELECT COUNT(*) FROM clientes_retraso_snapshot);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 7. TRIGGER: actualizar snapshot en cambios de cuota
-- ============================================================================
DROP TRIGGER IF EXISTS trigger_actualizar_retraso_snapshot ON cuotas;
CREATE TRIGGER trigger_actualizar_retraso_snapshot
AFTER INSERT OR UPDATE ON cuotas
FOR EACH ROW
EXECUTE FUNCTION actualizar_retraso_snapshot();

-- 8. FUNCIÓN: limpiar_caches_expirados
-- ============================================================================
CREATE OR REPLACE FUNCTION limpiar_caches_expirados()
RETURNS void AS $$
DECLARE
    deleted_email INT;
    deleted_adjuntos INT;
BEGIN
    -- Limpiar email config cache expirada
    DELETE FROM email_config_cache 
    WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_email = ROW_COUNT;
    
    -- Limpiar adjuntos fijos cache (> 24h)
    DELETE FROM adjuntos_fijos_cache 
    WHERE updated_at < NOW() - INTERVAL '24 hours';
    GET DIAGNOSTICS deleted_adjuntos = ROW_COUNT;
    
    RAISE NOTICE '[CRON] Cachés limpiados: email_config=%s, adjuntos=%s', 
        deleted_email, deleted_adjuntos;
END;
$$ LANGUAGE plpgsql;

-- 9. ÍNDICES ADICIONALES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_pagos_estado_fecha 
ON pagos (estado, fecha_pago DESC) 
WHERE estado = 'PAGADO';

CREATE INDEX IF NOT EXISTS idx_cuotas_vencidas 
ON cuotas (prestamo_id, fecha_pago) 
WHERE fecha_pago < CURRENT_DATE AND estado != 'CANCELADA';

CREATE INDEX IF NOT EXISTS idx_cliente_cedula_estado 
ON clientes (cedula) 
WHERE estado = 'ACTIVO';

-- ============================================================================
-- VERIFICACIÓN POST-MIGRACIÓN
-- ============================================================================

-- Verificar que todas las vistas fueron creadas
SELECT 
    'clientes_retrasados_mv' as vista,
    COUNT(*) as filas
FROM clientes_retrasados_mv
UNION ALL
SELECT 
    'pagos_kpis_mv' as vista,
    COUNT(*) as filas
FROM pagos_kpis_mv;

-- Verificar tablas de caché
SELECT 
    'adjuntos_fijos_cache' as tabla,
    COUNT(*) as filas
FROM adjuntos_fijos_cache
UNION ALL
SELECT 
    'email_config_cache' as tabla,
    COUNT(*) as filas
FROM email_config_cache
UNION ALL
SELECT 
    'clientes_retraso_snapshot' as tabla,
    COUNT(*) as filas
FROM clientes_retraso_snapshot;

-- Verificar que los triggers están activos
SELECT 
    trigger_name,
    event_object_table as tabla,
    action_timing,
    event_manipulation
FROM information_schema.triggers
WHERE trigger_name = 'trigger_actualizar_retraso_snapshot';

-- Verificar que los índices fueron creados
SELECT 
    indexname,
    tablename,
    pg_size_pretty(pg_relation_size(indexrelid)) as tamaño
FROM pg_indexes
WHERE indexname IN (
    'idx_clientes_retrasados_mv_cedula',
    'idx_pagos_kpis_mv_fecha',
    'idx_adjuntos_fijos_cache_caso',
    'idx_email_config_cache_key',
    'idx_pagos_estado_fecha',
    'idx_cuotas_vencidas',
    'idx_cliente_cedula_estado'
)
ORDER BY tablename, indexname;

-- ============================================================================
-- ESTADÍSTICAS
-- ============================================================================

-- Ver tamaño de vistas y tablas
SELECT 
    'clientes_retrasados_mv' as objeto,
    pg_size_pretty(pg_total_relation_size('clientes_retrasados_mv')) as tamaño
UNION ALL
SELECT 
    'pagos_kpis_mv' as objeto,
    pg_size_pretty(pg_total_relation_size('pagos_kpis_mv')) as tamaño
UNION ALL
SELECT 
    'clientes_retraso_snapshot' as objeto,
    pg_size_pretty(pg_total_relation_size('clientes_retraso_snapshot')) as tamaño
UNION ALL
SELECT 
    'adjuntos_fijos_cache' as objeto,
    pg_size_pretty(pg_total_relation_size('adjuntos_fijos_cache')) as tamaño
UNION ALL
SELECT 
    'email_config_cache' as objeto,
    pg_size_pretty(pg_total_relation_size('email_config_cache')) as tamaño;
