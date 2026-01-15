-- ============================================================================
-- ÍNDICES PARA OPTIMIZACIÓN DEL ENDPOINT /chat-ai
-- ============================================================================
-- Fecha: 2025-01-27
-- Propósito: Mejorar rendimiento de consultas realizadas por el Chat AI
-- Impacto esperado: Reducción de 30-50% en tiempo de respuesta
-- ============================================================================

-- ============================================================================
-- PRIORIDAD ALTA: Índices para GROUP BY con EXTRACT (consultas mensuales)
-- ============================================================================

-- 1. Índice para cuotas agrupadas por mes (usado en _obtener_resumen_bd)
-- Mejora: Consultas de información mensual de cuotas
-- Impacto: Reducción de 1000-2000ms a 200-400ms
CREATE INDEX IF NOT EXISTS idx_cuotas_extract_year_month_vencimiento
ON cuotas (
    EXTRACT(YEAR FROM fecha_vencimiento),
    EXTRACT(MONTH FROM fecha_vencimiento)
)
WHERE fecha_vencimiento IS NOT NULL;

-- 2. Índice para préstamos agrupados por mes (usado en consultas dinámicas)
-- Mejora: Consultas por período en _ejecutar_consulta_dinamica
-- Impacto: Reducción de 5000-10000ms a 500-1000ms
CREATE INDEX IF NOT EXISTS idx_prestamos_extract_year_month_registro
ON prestamos (
    EXTRACT(YEAR FROM fecha_registro),
    EXTRACT(MONTH FROM fecha_registro)
)
WHERE fecha_registro IS NOT NULL
  AND estado = 'APROBADO';

-- 3. Índice para pagos agrupados por mes (usado en consultas dinámicas)
-- Mejora: Consultas de pagos por período
-- Impacto: Reducción de 2000-3000ms a 300-500ms
CREATE INDEX IF NOT EXISTS idx_pagos_extract_year_month
ON pagos (
    EXTRACT(YEAR FROM fecha_pago),
    EXTRACT(MONTH FROM fecha_pago)
)
WHERE fecha_pago IS NOT NULL
  AND activo = TRUE;

-- ============================================================================
-- PRIORIDAD MEDIA: Índices compuestos para JOINs eficientes
-- ============================================================================

-- 4. Índice compuesto para cuotas con JOINs a préstamos
-- Mejora: JOINs en _obtener_resumen_bd y consultas dinámicas
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_estado_fecha_vencimiento
ON cuotas (prestamo_id, estado, fecha_vencimiento)
WHERE fecha_vencimiento IS NOT NULL;

-- 5. Índice compuesto para préstamos con filtros frecuentes
-- Mejora: Consultas por analista y estado en _ejecutar_consulta_dinamica
CREATE INDEX IF NOT EXISTS idx_prestamos_estado_analista_cedula
ON prestamos (estado, analista, cedula)
WHERE estado IN ('APROBADO', 'ACTIVO', 'PENDIENTE');

-- 6. Índice compuesto para pagos con filtros frecuentes
-- Mejora: Consultas de pagos por período y estado
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_activo_prestamo
ON pagos (fecha_pago, activo, prestamo_id)
WHERE fecha_pago IS NOT NULL
  AND activo = TRUE;

-- ============================================================================
-- PRIORIDAD BAJA: Índices adicionales para optimizaciones específicas
-- ============================================================================

-- 7. Índice para búsqueda por analista (usado en consultas dinámicas)
-- Mejora: Búsqueda de préstamos por analista con ILIKE
CREATE INDEX IF NOT EXISTS idx_prestamos_analista_trgm
ON prestamos USING gin (analista gin_trgm_ops)
WHERE analista IS NOT NULL;

-- Nota: Requiere extensión pg_trgm
-- Ejecutar primero: CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- VERIFICACIÓN DE ÍNDICES CREADOS
-- ============================================================================

-- Consulta para verificar que los índices se crearon correctamente:
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     indexdef
-- FROM pg_indexes
-- WHERE indexname LIKE 'idx_%chat_ai%'
--    OR indexname IN (
--        'idx_cuotas_extract_year_month_vencimiento',
--        'idx_prestamos_extract_year_month_registro',
--        'idx_pagos_extract_year_month',
--        'idx_cuotas_prestamo_estado_fecha_vencimiento',
--        'idx_prestamos_estado_analista_cedula',
--        'idx_pagos_fecha_activo_prestamo',
--        'idx_prestamos_analista_trgm'
--    )
-- ORDER BY tablename, indexname;

-- ============================================================================
-- NOTAS IMPORTANTES
-- ============================================================================
-- 1. Los índices funcionales con EXTRACT pueden tardar varios minutos en crearse
--    en tablas grandes (> 1M registros)
-- 2. Ejecutar durante horarios de bajo tráfico
-- 3. El índice con pg_trgm requiere la extensión pg_trgm instalada
-- 4. Verificar que los índices se usan con EXPLAIN ANALYZE en las queries
-- ============================================================================
