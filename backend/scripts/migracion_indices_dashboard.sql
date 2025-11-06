-- ============================================================================
-- MIGRACIÓN: ÍNDICES CRÍTICOS PARA OPTIMIZAR DASHBOARD
-- ============================================================================
-- Este script crea índices específicos para mejorar el rendimiento de las
-- queries del dashboard identificadas en OPTIMIZACION_CONSULTAS_BD.md
--
-- ⚠️ IMPORTANTE: Ejecutar durante horarios de bajo tráfico
-- Los índices pueden tardar varios minutos en crearse en tablas grandes
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. ÍNDICES PARA GROUP BY POR AÑO/MES (CRÍTICO)
-- ============================================================================
-- Mejoran queries que agrupan por EXTRACT(YEAR/MONTH) en fecha_aprobacion

-- Índice para préstamos agrupados por año/mes de aprobación
CREATE INDEX IF NOT EXISTS idx_prestamos_fecha_aprobacion_ym 
ON prestamos (
    EXTRACT(YEAR FROM fecha_aprobacion),
    EXTRACT(MONTH FROM fecha_aprobacion),
    estado
)
WHERE estado = 'APROBADO' 
  AND fecha_aprobacion IS NOT NULL;

COMMENT ON INDEX idx_prestamos_fecha_aprobacion_ym IS 
'Optimiza GROUP BY por año/mes en obtener_financiamiento_tendencia_mensual y obtener_kpis_principales';

-- Índice para cuotas agrupadas por año/mes de vencimiento
CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento_ym 
ON cuotas (
    EXTRACT(YEAR FROM fecha_vencimiento),
    EXTRACT(MONTH FROM fecha_vencimiento)
)
WHERE fecha_vencimiento IS NOT NULL;

COMMENT ON INDEX idx_cuotas_fecha_vencimiento_ym IS 
'Optimiza GROUP BY por año/mes en queries de cuotas programadas y pagadas';

-- ============================================================================
-- 2. ÍNDICES COMPUESTOS PARA JOINs EFICIENTES (ALTO)
-- ============================================================================

-- Índice compuesto para JOIN cuotas-prestamos con filtros comunes
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_fecha_vencimiento 
ON cuotas (prestamo_id, fecha_vencimiento, estado, total_pagado, monto_cuota);

COMMENT ON INDEX idx_cuotas_prestamo_fecha_vencimiento IS 
'Optimiza JOINs entre cuotas y prestamos, reduce N+1 queries';

-- Índice para búsquedas por cédula con estado
CREATE INDEX IF NOT EXISTS idx_prestamos_cedula_estado 
ON prestamos (cedula, estado)
WHERE estado IN ('APROBADO', 'FINALIZADO');

COMMENT ON INDEX idx_prestamos_cedula_estado IS 
'Optimiza obtener_resumen_prestamos_cliente y queries por cédula';

-- Índice compuesto para filtros de fecha_aprobacion con estado y analista
CREATE INDEX IF NOT EXISTS idx_prestamos_aprobacion_estado_analista 
ON prestamos (fecha_aprobacion, estado, analista, concesionario)
WHERE estado = 'APROBADO' 
  AND fecha_aprobacion IS NOT NULL;

COMMENT ON INDEX idx_prestamos_aprobacion_estado_analista IS 
'Optimiza queries con filtros de analista/concesionario y fechas';

-- ============================================================================
-- 3. ÍNDICES PARA PAGOS (MEDIO)
-- ============================================================================

-- Índice para filtros de fecha en pagos activos
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_pago_activo 
ON pagos (fecha_pago, activo, monto_pagado)
WHERE activo = TRUE 
  AND monto_pagado > 0;

COMMENT ON INDEX idx_pagos_fecha_pago_activo IS 
'Optimiza queries de pagos por fecha y monto';

-- Índice para JOIN pagos-prestamos
CREATE INDEX IF NOT EXISTS idx_pagos_prestamo_fecha 
ON pagos (prestamo_id, fecha_pago, activo)
WHERE activo = TRUE;

COMMENT ON INDEX idx_pagos_prestamo_fecha IS 
'Optimiza JOINs entre pagos y prestamos';

-- ============================================================================
-- 4. ÍNDICES ADICIONALES PARA FILTROS COMUNES (BAJO)
-- ============================================================================

-- Índice para filtros por concesionario
CREATE INDEX IF NOT EXISTS idx_prestamos_concesionario_estado 
ON prestamos (concesionario, estado)
WHERE estado = 'APROBADO';

-- Índice para filtros por modelo
CREATE INDEX IF NOT EXISTS idx_prestamos_modelo_estado 
ON prestamos (modelo_vehiculo, estado)
WHERE estado = 'APROBADO' 
  AND modelo_vehiculo IS NOT NULL;

-- ============================================================================
-- VERIFICACIÓN DE ÍNDICES CREADOS
-- ============================================================================

-- Mostrar índices creados
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE 'idx_%_dashboard%' 
   OR indexname LIKE 'idx_prestamos_%'
   OR indexname LIKE 'idx_cuotas_%'
   OR indexname LIKE 'idx_pagos_%'
ORDER BY tablename, indexname;

COMMIT;

-- ============================================================================
-- NOTAS POST-MIGRACIÓN
-- ============================================================================
-- 1. Verificar que los índices se usen con:
--    EXPLAIN ANALYZE SELECT ... FROM prestamos WHERE ...
--
-- 2. Monitorear tamaño de índices:
--    SELECT pg_size_pretty(pg_relation_size('idx_prestamos_fecha_aprobacion_ym'));
--
-- 3. Si algún índice no se usa después de 1 semana, considerar eliminarlo:
--    DROP INDEX IF EXISTS idx_nombre_indice;
-- ============================================================================

