-- ============================================================================
-- MIGRACIÓN MANUAL: Índices para optimizar APIs públicas
-- Fecha: 2026-03-30
-- Propósito: Reducir latencia en endpoints estado_cuenta_publico y cobros_publico
-- ============================================================================

-- 1. Índice: Búsqueda rápida de clientes por cédula
-- Usado en: /validar-cedula (estado_cuenta_publico, cobros_publico)
-- Mejora esperada: 271ms → ~50ms
CREATE INDEX IF NOT EXISTS idx_cliente_cedula ON clientes (cedula)
WHERE cedula IS NOT NULL;

-- 2. Índice: Códigos de estado de cuenta activos
-- Usado en: /solicitar-codigo, /verificar-codigo
-- Mejora esperada: Búsquedas más rápidas de códigos no expirados
CREATE INDEX IF NOT EXISTS idx_estado_cuenta_codigo_cedula_activo 
ON estado_cuenta_codigos (cedula_normalizada, usado, expira_en)
WHERE usado = FALSE;

-- 3. Índice: Préstamos por cliente y estado APROBADO
-- Usado en: /enviar-reporte (validación de cliente)
-- Mejora esperada: Validaciones instantáneas
CREATE INDEX IF NOT EXISTS idx_prestamo_cliente_estado 
ON prestamos (cliente_id, estado)
WHERE estado = 'APROBADO';

-- 4. Índice: Pagos reportados por cédula y estado
-- Usado en: Dashboard de cobros (pagos-reportados/listado-y-kpis)
-- Mejora esperada: 918ms → ~300ms
CREATE INDEX IF NOT EXISTS idx_pago_reportado_cedula_estado 
ON pagos_reportados (tipo_cedula, numero_cedula, estado);

-- 5. Índice: Cuotas por préstamo (generación de PDFs)
-- Usado en: /recibo-cuota (estado_cuenta_publico)
-- Mejora esperada: 1170ms → ~300ms
CREATE INDEX IF NOT EXISTS idx_cuota_prestamo 
ON cuotas (prestamo_id, numero_cuota)
WHERE estado != 'CANCELADA';

-- ============================================================================
-- ANÁLISIS DE ÍNDICES CREADOS
-- ============================================================================

-- Verificar que todos los índices fueron creados exitosamente:
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname IN (
    'idx_cliente_cedula',
    'idx_estado_cuenta_codigo_cedula_activo',
    'idx_prestamo_cliente_estado',
    'idx_pago_reportado_cedula_estado',
    'idx_cuota_prestamo'
)
ORDER BY tablename, indexname;

-- ============================================================================
-- ESTADÍSTICAS DE ÍNDICES (ejecutar después de un tiempo de uso)
-- ============================================================================

-- Verificar uso de índices:
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as num_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE indexname IN (
    'idx_cliente_cedula',
    'idx_estado_cuenta_codigo_cedula_activo',
    'idx_prestamo_cliente_estado',
    'idx_pago_reportado_cedula_estado',
    'idx_cuota_prestamo'
)
ORDER BY idx_scan DESC;

-- ============================================================================
-- LIMPIEZA (si necesitas remover índices - NO EJECUTAR sin revisar)
-- ============================================================================

/*
-- Para REMOVER TODOS los índices (si falla algo):
DROP INDEX IF EXISTS idx_cliente_cedula;
DROP INDEX IF EXISTS idx_estado_cuenta_codigo_cedula_activo;
DROP INDEX IF EXISTS idx_prestamo_cliente_estado;
DROP INDEX IF EXISTS idx_pago_reportado_cedula_estado;
DROP INDEX IF EXISTS idx_cuota_prestamo;
*/

-- ============================================================================
-- VERIFICACIÓN DE PERFORMANCE (ANTES/DESPUÉS)
-- ============================================================================

-- ANTES: sin índices (comentado)
/*
EXPLAIN ANALYZE
SELECT c.* FROM clientes c 
WHERE c.cedula = 'V12345678';

EXPLAIN ANALYZE
SELECT ecc.* FROM estado_cuenta_codigos ecc 
WHERE ecc.cedula_normalizada = 'V12345678' 
  AND ecc.usado = FALSE 
  AND ecc.expira_en > NOW();

EXPLAIN ANALYZE
SELECT p.* FROM prestamos p 
WHERE p.cliente_id = 123 
  AND p.estado = 'APROBADO';

EXPLAIN ANALYZE
SELECT pr.* FROM pagos_reportados pr 
WHERE pr.tipo_cedula = 'V' 
  AND pr.numero_cedula = '12345678' 
  AND pr.estado = 'aprobado';

EXPLAIN ANALYZE
SELECT c.* FROM cuotas c 
WHERE c.prestamo_id = 456 
  AND c.estado != 'CANCELADA'
ORDER BY c.numero_cuota;
*/

-- DESPUÉS: con índices (ejecutar para verificar)
EXPLAIN ANALYZE
SELECT c.* FROM clientes c 
WHERE c.cedula = 'V12345678';

EXPLAIN ANALYZE
SELECT ecc.* FROM estado_cuenta_codigos ecc 
WHERE ecc.cedula_normalizada = 'V12345678' 
  AND ecc.usado = FALSE 
  AND ecc.expira_en > NOW();

EXPLAIN ANALYZE
SELECT p.* FROM prestamos p 
WHERE p.cliente_id = 123 
  AND p.estado = 'APROBADO';

EXPLAIN ANALYZE
SELECT pr.* FROM pagos_reportados pr 
WHERE pr.tipo_cedula = 'V' 
  AND pr.numero_cedula = '12345678' 
  AND pr.estado = 'aprobado';

EXPLAIN ANALYZE
SELECT c.* FROM cuotas c 
WHERE c.prestamo_id = 456 
  AND c.estado != 'CANCELADA'
ORDER BY c.numero_cuota;

-- ============================================================================
-- NOTAS DE IMPLEMENTACIÓN
-- ============================================================================

/*
IMPACTO ESPERADO:

1. idx_cliente_cedula
   - Antes: Seq Scan (full table scan)
   - Después: Index Scan (< 1ms)
   - Endpoints: validar-cedula
   - Mejora: 271ms → ~50ms

2. idx_estado_cuenta_codigo_cedula_activo
   - Antes: Seq Scan + Filter
   - Después: Index Scan (composite index)
   - Endpoints: solicitar-codigo, verificar-codigo
   - Mejora: Búsquedas < 5ms

3. idx_prestamo_cliente_estado
   - Antes: Seq Scan + Filter
   - Después: Index Scan
   - Endpoints: enviar-reporte (validación)
   - Mejora: Validación instantánea

4. idx_pago_reportado_cedula_estado
   - Antes: Seq Scan (big table)
   - Después: Index Scan
   - Endpoints: pagos-reportados/listado-y-kpis
   - Mejora: 918ms → ~300ms

5. idx_cuota_prestamo
   - Antes: Seq Scan (per cuota lookup)
   - Después: Index Scan
   - Endpoints: /recibo-cuota
   - Mejora: 1170ms → ~300ms

MONITOREO POST-IMPLEMENTACIÓN:

1. Ejecutar EXPLAIN ANALYZE en cada query
2. Verificar pg_stat_user_indexes para uso
3. Medir latencia en endpoints públicos
4. Ajustar si es necesario (REINDEX IF NEEDED)

MANTENIMIENTO:

- VACUUM ANALYZE (mensualmente)
- REINDEX (si fragmentación > 20%)
- Monitor con pg_stat_user_indexes
*/
