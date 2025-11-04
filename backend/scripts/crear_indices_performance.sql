-- ============================================================================
-- SCRIPT DE CREACIÓN DE ÍNDICES PARA MEJORAR PERFORMANCE
-- ============================================================================
-- Este script crea índices funcionales y regulares para optimizar las queries
-- más comunes del dashboard y endpoints de reportes.
--
-- ✅ CORRECCIÓN: Se usa DATE_TRUNC en lugar de EXTRACT para índices funcionales
-- porque DATE_TRUNC es IMMUTABLE (requisito de PostgreSQL para índices funcionales)
--
-- 📋 TABLAS CUBIERTAS:
--   - pagos_staging (fecha_pago, conciliado, cedula_cliente)
--   - cuotas (fecha_vencimiento, fecha_pago, prestamo_id, estado)
--   - prestamos (fecha_registro, estado, cedula, cliente_id, usuario_proponente)
--   - pagos (fecha_pago, activo, conciliado, prestamo_id)
--   - clientes (cedula, fecha_registro, estado, id)
--   - users (email)
--   - notificaciones (enviada_en, cliente_id, tipo)
--   - aprobaciones (fecha_solicitud, estado)
--   - dashboard_morosidad_mensual (año, mes)
--
-- ⚠️ IMPORTANTE: Ejecutar durante horarios de bajo tráfico
-- Los índices pueden tardar varios minutos en crearse en tablas grandes
-- ============================================================================

-- ============================================================================
-- 1. ÍNDICES FUNCIONALES PARA GROUP BY POR AÑO/MES
-- ============================================================================
-- Estos índices mejoran significativamente las queries que agrupan por año/mes
-- usando EXTRACT(YEAR/MONTH)

-- Índice funcional para pagos_staging (GROUP BY por fecha_pago)
-- Mejora: /api/v1/pagos/kpis, /api/v1/dashboard/cobranzas-mensuales, /api/v1/dashboard/evolucion-pagos
-- ✅ Usar DATE_TRUNC que es IMMUTABLE en lugar de EXTRACT
CREATE INDEX IF NOT EXISTS idx_pagos_staging_fecha_pago_funcional 
ON pagos_staging (
    DATE_TRUNC('month', (fecha_pago::timestamp)::date)
)
WHERE fecha_pago IS NOT NULL 
  AND fecha_pago != '' 
  AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}';

-- Índice alternativo: índice regular en fecha_pago para mejorar filtros
CREATE INDEX IF NOT EXISTS idx_pagos_staging_fecha_pago_regular 
ON pagos_staging (fecha_pago)
WHERE fecha_pago IS NOT NULL 
  AND fecha_pago != '' 
  AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}';

-- Índice funcional para cuotas (GROUP BY por fecha_vencimiento)
-- Mejora: /api/v1/dashboard/cobranzas-mensuales, /api/v1/dashboard/evolucion-morosidad
-- ✅ Usar DATE_TRUNC que es IMMUTABLE
CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento_funcional 
ON cuotas (
    DATE_TRUNC('month', fecha_vencimiento)
)
WHERE fecha_vencimiento IS NOT NULL;

-- Índice funcional para cuotas (GROUP BY por fecha_pago)
-- Mejora: Queries que agrupan cuotas pagadas por mes
-- ✅ Usar DATE_TRUNC que es IMMUTABLE
CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_pago_funcional 
ON cuotas (
    DATE_TRUNC('month', fecha_pago)
)
WHERE fecha_pago IS NOT NULL;

-- Índice funcional para prestamos (GROUP BY por fecha_registro)
-- Mejora: /api/v1/dashboard/financiamiento-tendencia-mensual, /api/v1/dashboard/evolucion-general-mensual
-- ✅ Usar DATE_TRUNC que es IMMUTABLE
CREATE INDEX IF NOT EXISTS idx_prestamos_fecha_registro_funcional 
ON prestamos (
    DATE_TRUNC('month', fecha_registro)
)
WHERE fecha_registro IS NOT NULL
  AND estado = 'APROBADO';

-- Índice funcional para pagos (GROUP BY por fecha_pago)
-- Mejora: /api/v1/dashboard/evolucion-general-mensual
-- ✅ Usar DATE_TRUNC que es IMMUTABLE
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_pago_funcional 
ON pagos (
    DATE_TRUNC('month', fecha_pago)
)
WHERE fecha_pago IS NOT NULL
  AND activo = TRUE;

-- ============================================================================
-- 2. ÍNDICES REGULARES PARA FILTROS Y JOINs
-- ============================================================================

-- Índices para pagos_staging
-- Mejora filtros por fecha_pago (usar expresión que PostgreSQL pueda convertir)
-- Nota: PostgreSQL puede usar índices en TEXT para comparaciones de timestamp
CREATE INDEX IF NOT EXISTS idx_pagos_staging_fecha_pago_text 
ON pagos_staging (fecha_pago)
WHERE fecha_pago IS NOT NULL 
  AND fecha_pago != ''
  AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}';

-- Mejora filtros por conciliado
CREATE INDEX IF NOT EXISTS idx_pagos_staging_conciliado 
ON pagos_staging (conciliado)
WHERE conciliado IS NOT NULL;

-- Índices para cuotas
-- Mejora JOINs con prestamos
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_id 
ON cuotas (prestamo_id);

-- Mejora filtros por estado
CREATE INDEX IF NOT EXISTS idx_cuotas_estado 
ON cuotas (estado);

-- Mejora filtros por fecha_vencimiento
CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento 
ON cuotas (fecha_vencimiento);

-- Índices para prestamos
-- Mejora filtros por estado (muy usado)
CREATE INDEX IF NOT EXISTS idx_prestamos_estado 
ON prestamos (estado);

-- Mejora filtros y ordenamiento por fecha_registro
CREATE INDEX IF NOT EXISTS idx_prestamos_fecha_registro 
ON prestamos (fecha_registro);

-- Mejora JOINs con clientes
CREATE INDEX IF NOT EXISTS idx_prestamos_cedula 
ON prestamos (cedula);

-- Mejora filtros por analista
CREATE INDEX IF NOT EXISTS idx_prestamos_usuario_proponente 
ON prestamos (usuario_proponente);

-- Índices para pagos
-- Mejora JOINs con prestamos
CREATE INDEX IF NOT EXISTS idx_pagos_prestamo_id 
ON pagos (prestamo_id);

-- Mejora filtros por fecha_pago
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_pago 
ON pagos (fecha_pago);

-- Mejora filtros por activo
CREATE INDEX IF NOT EXISTS idx_pagos_activo 
ON pagos (activo);

-- Mejora filtros por conciliado
CREATE INDEX IF NOT EXISTS idx_pagos_conciliado 
ON pagos (conciliado);

-- Índices para clientes
-- Mejora búsquedas y JOINs por cédula
CREATE INDEX IF NOT EXISTS idx_clientes_cedula 
ON clientes (cedula);

-- Mejora ordenamiento y filtros por fecha_registro
CREATE INDEX IF NOT EXISTS idx_clientes_fecha_registro 
ON clientes (fecha_registro);

-- Mejora filtros por estado
CREATE INDEX IF NOT EXISTS idx_clientes_estado 
ON clientes (estado);

-- Mejora JOINs directos con prestamos por cliente_id
CREATE INDEX IF NOT EXISTS idx_clientes_id 
ON clientes (id);

-- Índices para users
-- Mejora JOINs con prestamos.usuario_proponente (muy usado en dashboard)
CREATE INDEX IF NOT EXISTS idx_users_email 
ON users (email)
WHERE email IS NOT NULL;

-- Índices para notificaciones
-- Mejora filtros por fecha de envío (usado en notificaciones automáticas)
CREATE INDEX IF NOT EXISTS idx_notificaciones_enviada_en 
ON notificaciones (enviada_en)
WHERE enviada_en IS NOT NULL;

-- Mejora filtros compuestos por cliente y tipo (usado en notificaciones automáticas)
CREATE INDEX IF NOT EXISTS idx_notificaciones_cliente_tipo_enviada 
ON notificaciones (cliente_id, tipo, enviada_en)
WHERE cliente_id IS NOT NULL;

-- Índices para aprobaciones
-- Mejora filtros por fecha de solicitud
CREATE INDEX IF NOT EXISTS idx_aprobaciones_fecha_solicitud 
ON aprobaciones (fecha_solicitud);

-- Mejora filtros compuestos por estado y fecha
CREATE INDEX IF NOT EXISTS idx_aprobaciones_estado_fecha 
ON aprobaciones (estado, fecha_solicitud)
WHERE estado = 'PENDIENTE';

-- Índices para pagos_staging
-- Mejora filtros por cédula del cliente
CREATE INDEX IF NOT EXISTS idx_pagos_staging_cedula_cliente 
ON pagos_staging (cedula_cliente)
WHERE cedula_cliente IS NOT NULL 
  AND cedula_cliente != '';

-- Índices para prestamos
-- Mejora JOINs directos con clientes por cliente_id
CREATE INDEX IF NOT EXISTS idx_prestamos_cliente_id 
ON prestamos (cliente_id);

-- ============================================================================
-- 3. ÍNDICES COMPUESTOS PARA QUERIES ESPECÍFICAS
-- ============================================================================

-- Índice compuesto para dashboard_morosidad_mensual (ya debería existir)
-- Mejora: /api/v1/dashboard/evolucion-morosidad
CREATE INDEX IF NOT EXISTS idx_dashboard_morosidad_año_mes 
ON dashboard_morosidad_mensual (año, mes);

-- Índice compuesto para cuotas con estado y fecha_vencimiento
-- Mejora queries de morosidad
CREATE INDEX IF NOT EXISTS idx_cuotas_estado_fecha_vencimiento 
ON cuotas (estado, fecha_vencimiento)
WHERE estado != 'PAGADO';

-- Índice compuesto para prestamos con estado y fecha_registro
-- Mejora queries de dashboard admin
CREATE INDEX IF NOT EXISTS idx_prestamos_estado_fecha_registro 
ON prestamos (estado, fecha_registro)
WHERE estado = 'APROBADO';

-- Índice compuesto para pagos con activo y fecha_pago
-- Mejora queries de pagos activos por fecha
CREATE INDEX IF NOT EXISTS idx_pagos_activo_fecha_pago 
ON pagos (activo, fecha_pago)
WHERE activo = TRUE;

-- ============================================================================
-- 4. VERIFICACIÓN DE ÍNDICES CREADOS
-- ============================================================================

-- Descomentar para verificar los índices creados:
-- SELECT 
--     schemaname,
--     tablename,
--     indexname,
--     indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'public'
--   AND indexname LIKE 'idx_%'
-- ORDER BY tablename, indexname;

-- ============================================================================
-- 5. ESTADÍSTICAS DE ÍNDICES
-- ============================================================================

-- Descomentar para ver tamaño de índices:
-- SELECT 
--     schemaname,
--     tablename,
--     indexname,
--     pg_size_pretty(pg_relation_size(indexrelid)) as index_size
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
--   AND indexname LIKE 'idx_%'
-- ORDER BY pg_relation_size(indexrelid) DESC;

-- ============================================================================
-- NOTAS IMPORTANTES
-- ============================================================================
-- 1. Los índices funcionales pueden tardar varios minutos en crearse en tablas grandes
-- 2. Ejecutar este script durante horarios de bajo tráfico
-- 3. Los índices ocupan espacio en disco adicional
-- 4. Después de crear los índices, ejecutar ANALYZE para actualizar estadísticas:
--    ANALYZE pagos_staging;
--    ANALYZE cuotas;
--    ANALYZE prestamos;
--    ANALYZE pagos;
--    ANALYZE clientes;
--    ANALYZE users;
--    ANALYZE notificaciones;
--    ANALYZE aprobaciones;
--
-- 5. Para verificar que los índices están siendo usados, usar EXPLAIN ANALYZE:
--    EXPLAIN ANALYZE
--    SELECT EXTRACT(YEAR FROM fecha_pago::timestamp), EXTRACT(MONTH FROM fecha_pago::timestamp), SUM(monto_pagado::numeric)
--    FROM pagos_staging
--    WHERE fecha_pago IS NOT NULL
--    GROUP BY EXTRACT(YEAR FROM fecha_pago::timestamp), EXTRACT(MONTH FROM fecha_pago::timestamp);
-- ============================================================================

