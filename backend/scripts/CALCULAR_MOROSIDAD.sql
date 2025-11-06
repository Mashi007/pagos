-- ============================================================================
-- QUERY: CALCULAR MOROSIDAD POR MES
-- ============================================================================
-- Esta query calcula la morosidad exactamente como lo hace el sistema
-- 
-- Uso:
--   1. Modificar las fechas :fecha_inicio y :fecha_fin_total según necesidad
--   2. Ejecutar en DBeaver
--   3. Revisar los resultados agrupados por mes y año
--
-- ============================================================================

-- ============================================================================
-- CONFIGURACIÓN: Cambiar las fechas aquí
-- ============================================================================
-- Por defecto: últimos 6 meses desde hoy
-- Para cambiar el rango, modifica las fechas en las consultas siguientes

-- ============================================================================
-- QUERY 1: MOROSIDAD POR MES (Últimos 6 meses)
-- ============================================================================
-- Esta es la query exacta que usa el sistema para calcular morosidad
SELECT 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    TO_CHAR(EXTRACT(MONTH FROM c.fecha_vencimiento), 'FM00') || '/' || 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::text as mes_año,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad_total,
    TO_CHAR(COALESCE(SUM(c.monto_cuota), 0), 'FM$999,999,999,990.00') as morosidad_formateada,
    COUNT(*) as cantidad_cuotas
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento >= CURRENT_DATE - INTERVAL '6 months'  -- Últimos 6 meses
    AND c.fecha_vencimiento < CURRENT_DATE                          -- Hasta hoy (sin incluir)
    AND c.estado != 'PAGADO'
GROUP BY 
    EXTRACT(YEAR FROM c.fecha_vencimiento), 
    EXTRACT(MONTH FROM c.fecha_vencimiento)
ORDER BY año, mes;

-- ============================================================================
-- QUERY 2: MOROSIDAD CON RANGO DE FECHAS ESPECÍFICO
-- ============================================================================
-- Descomenta y modifica las fechas para un rango específico
/*
SELECT 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    TO_CHAR(EXTRACT(MONTH FROM c.fecha_vencimiento), 'FM00') || '/' || 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::text as mes_año,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad_total,
    TO_CHAR(COALESCE(SUM(c.monto_cuota), 0), 'FM$999,999,999,990.00') as morosidad_formateada,
    COUNT(*) as cantidad_cuotas
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento >= '2024-08-01'::date  -- Cambiar fecha inicio
    AND c.fecha_vencimiento < '2025-01-01'::date    -- Cambiar fecha fin
    AND c.estado != 'PAGADO'
GROUP BY 
    EXTRACT(YEAR FROM c.fecha_vencimiento), 
    EXTRACT(MONTH FROM c.fecha_vencimiento)
ORDER BY año, mes;
*/

-- ============================================================================
-- QUERY 3: MOROSIDAD TOTAL (Sin agrupar por mes)
-- ============================================================================
-- Muestra el total de morosidad acumulada
SELECT 
    'TOTAL MOROSIDAD' AS resumen,
    COUNT(*) as total_cuotas_vencidas,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad_total,
    TO_CHAR(COALESCE(SUM(c.monto_cuota), 0), 'FM$999,999,999,990.00') as morosidad_formateada,
    MIN(c.fecha_vencimiento) as fecha_vencimiento_mas_antigua,
    MAX(c.fecha_vencimiento) as fecha_vencimiento_mas_reciente
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento < CURRENT_DATE  -- Solo cuotas vencidas
    AND c.estado != 'PAGADO';

-- ============================================================================
-- QUERY 4: DETALLE DE CUOTAS EN MORA (Útil para análisis)
-- ============================================================================
-- Muestra cada cuota individual que está en mora
SELECT 
    p.id as prestamo_id,
    p.cedula as cedula_cliente,
    c.id as cuota_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    CURRENT_DATE - c.fecha_vencimiento::date as dias_mora,
    c.monto_cuota,
    c.estado as estado_cuota,
    TO_CHAR(c.monto_cuota, 'FM$999,999,999,990.00') as monto_formateado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento < CURRENT_DATE
    AND c.estado != 'PAGADO'
ORDER BY 
    c.fecha_vencimiento DESC,  -- Más recientes primero
    p.id,
    c.numero_cuota
LIMIT 100;  -- Limitar a 100 registros para no sobrecargar

-- ============================================================================
-- QUERY 5: MOROSIDAD POR ESTADO DE CUOTA
-- ============================================================================
-- Ver distribución de morosidad según el estado de la cuota
SELECT 
    c.estado as estado_cuota,
    COUNT(*) as cantidad_cuotas,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad_por_estado,
    TO_CHAR(COALESCE(SUM(c.monto_cuota), 0), 'FM$999,999,999,990.00') as morosidad_formateada,
    ROUND(
        (COALESCE(SUM(c.monto_cuota), 0)::numeric / 
         NULLIF((SELECT SUM(monto_cuota) FROM cuotas c2 
                INNER JOIN prestamos p2 ON c2.prestamo_id = p2.id 
                WHERE p2.estado = 'APROBADO' 
                AND c2.fecha_vencimiento < CURRENT_DATE 
                AND c2.estado != 'PAGADO'), 0)) * 100, 
        2
    ) as porcentaje_del_total
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento < CURRENT_DATE
    AND c.estado != 'PAGADO'
GROUP BY c.estado
ORDER BY morosidad_por_estado DESC;

-- ============================================================================
-- INFORMACIÓN DE REFERENCIA
-- ============================================================================
-- Tablas consultadas:
--   ✅ cuotas (tabla principal)
--     - Campo: fecha_vencimiento (filtro y agrupación)
--     - Campo: monto_cuota (suma para calcular morosidad)
--     - Campo: estado (filtro: estado != 'PAGADO')
--     - Campo: prestamo_id (JOIN)
--
--   ✅ prestamos (tabla secundaria)
--     - Campo: id (JOIN)
--     - Campo: estado (filtro: estado = 'APROBADO')
--
-- Tablas NO consultadas:
--   ❌ pagos_staging
--   ❌ pagos
--   ❌ cobros
--   ❌ pago_cuotas
--   ❌ clientes
--
-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

