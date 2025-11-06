-- ============================================================================
-- 🔍 INVESTIGACIÓN EXHAUSTIVA DEL DASHBOARD - QUERIES PARA DBEAVER
-- ============================================================================
-- Fecha: 2025-01-06
-- Objetivo: Verificar TODOS los datos y métricas del dashboard
-- ============================================================================

-- ============================================================================
-- 1. VERIFICACIÓN DE ESTRUCTURA DE TABLAS Y TIPOS DE DATOS
-- ============================================================================

-- 1.1 Verificar estructura de tabla prestamos
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'prestamos'
ORDER BY ordinal_position;

-- 1.2 Verificar estructura de tabla cuotas
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'cuotas'
ORDER BY ordinal_position;

-- 1.3 Verificar estructura de tabla pagos
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'pagos'
ORDER BY ordinal_position;

-- 1.4 Verificar tipos de datos de fechas (CRÍTICO para errores datetime vs date)
SELECT 
    'prestamos' as tabla,
    'fecha_aprobacion' as columna,
    data_type,
    datetime_precision
FROM information_schema.columns
WHERE table_name = 'prestamos' AND column_name = 'fecha_aprobacion'
UNION ALL
SELECT 
    'prestamos' as tabla,
    'fecha_registro' as columna,
    data_type,
    datetime_precision
FROM information_schema.columns
WHERE table_name = 'prestamos' AND column_name = 'fecha_registro'
UNION ALL
SELECT 
    'cuotas' as tabla,
    'fecha_vencimiento' as columna,
    data_type,
    datetime_precision
FROM information_schema.columns
WHERE table_name = 'cuotas' AND column_name = 'fecha_vencimiento'
UNION ALL
SELECT 
    'pagos' as tabla,
    'fecha_pago' as columna,
    data_type,
    datetime_precision
FROM information_schema.columns
WHERE table_name = 'pagos' AND column_name = 'fecha_pago';

-- ============================================================================
-- 2. VERIFICACIÓN DE INTEGRIDAD DE DATOS
-- ============================================================================

-- 2.1 Préstamos sin estado válido
SELECT 
    estado,
    COUNT(*) as cantidad,
    SUM(total_financiamiento) as monto_total
FROM prestamos
GROUP BY estado
ORDER BY cantidad DESC;

-- 2.2 Préstamos con estados inconsistentes
SELECT 
    id,
    estado,
    fecha_aprobacion,
    total_financiamiento,
    CASE 
        WHEN estado = 'APROBADO' AND fecha_aprobacion IS NULL THEN 'APROBADO SIN FECHA'
        WHEN estado != 'APROBADO' AND fecha_aprobacion IS NOT NULL THEN 'NO APROBADO CON FECHA'
        ELSE 'OK'
    END as inconsistencia
FROM prestamos
WHERE (estado = 'APROBADO' AND fecha_aprobacion IS NULL)
   OR (estado != 'APROBADO' AND fecha_aprobacion IS NOT NULL)
LIMIT 100;

-- 2.3 Cuotas con estados inconsistentes
SELECT 
    estado,
    COUNT(*) as cantidad,
    SUM(monto_cuota) as monto_total,
    COUNT(CASE WHEN fecha_vencimiento < CURRENT_DATE AND estado != 'PAGADO' THEN 1 END) as vencidas_no_pagadas
FROM cuotas
GROUP BY estado
ORDER BY cantidad DESC;

-- 2.4 Cuotas sin préstamo asociado (integridad referencial)
SELECT COUNT(*) as cuotas_sin_prestamo
FROM cuotas c
LEFT JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.id IS NULL;

-- 2.5 Pagos sin préstamo asociado
SELECT COUNT(*) as pagos_sin_prestamo
FROM pagos pa
LEFT JOIN prestamos p ON pa.prestamo_id = p.id
WHERE p.id IS NULL;

-- 2.6 Pagos sin cuota asociada (verificar por prestamo_id y numero_cuota)
SELECT 
    COUNT(*) as total_pagos,
    COUNT(CASE WHEN prestamo_id IS NOT NULL AND numero_cuota IS NOT NULL THEN 1 END) as pagos_con_cuota_info,
    COUNT(CASE WHEN prestamo_id IS NULL OR numero_cuota IS NULL THEN 1 END) as pagos_sin_cuota_info
FROM pagos
WHERE activo = true;

-- ============================================================================
-- 3. VERIFICACIÓN DE MÉTRICAS DEL DASHBOARD ADMIN
-- ============================================================================

-- 3.1 CARTERA TOTAL (debe coincidir con dashboard/admin)
SELECT 
    'CARTERA TOTAL' as metrica,
    COUNT(*) as cantidad_prestamos,
    SUM(total_financiamiento) as monto_total,
    MIN(fecha_aprobacion) as primera_aprobacion,
    MAX(fecha_aprobacion) as ultima_aprobacion
FROM prestamos
WHERE estado = 'APROBADO';

-- 3.2 CARTERA VENCIDA (cuotas vencidas no pagadas)
SELECT 
    'CARTERA VENCIDA' as metrica,
    COUNT(DISTINCT c.prestamo_id) as prestamos_con_cuotas_vencidas,
    COUNT(c.id) as cuotas_vencidas,
    SUM(c.monto_cuota) as monto_vencido_total,
    MIN(c.fecha_vencimiento) as primera_cuota_vencida,
    MAX(c.fecha_vencimiento) as ultima_cuota_vencida
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.fecha_vencimiento < CURRENT_DATE
  AND c.estado != 'PAGADO'
  AND p.estado = 'APROBADO';

-- 3.3 CARTERA AL DÍA (cartera total - cartera vencida)
WITH cartera_total AS (
    SELECT SUM(total_financiamiento) as total
    FROM prestamos
    WHERE estado = 'APROBADO'
),
cartera_vencida AS (
    SELECT SUM(c.monto_cuota) as vencida
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE c.fecha_vencimiento < CURRENT_DATE
      AND c.estado != 'PAGADO'
      AND p.estado = 'APROBADO'
)
SELECT 
    'CARTERA AL DÍA' as metrica,
    ct.total as cartera_total,
    COALESCE(cv.vencida, 0) as cartera_vencida,
    ct.total - COALESCE(cv.vencida, 0) as cartera_al_dia
FROM cartera_total ct
CROSS JOIN cartera_vencida cv;

-- 3.4 PORCENTAJE DE MORA
WITH cartera_total AS (
    SELECT SUM(total_financiamiento) as total
    FROM prestamos
    WHERE estado = 'APROBADO'
),
cartera_vencida AS (
    SELECT SUM(c.monto_cuota) as vencida
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE c.fecha_vencimiento < CURRENT_DATE
      AND c.estado != 'PAGADO'
      AND p.estado = 'APROBADO'
)
SELECT 
    'PORCENTAJE MORA' as metrica,
    ct.total as cartera_total,
    COALESCE(cv.vencida, 0) as cartera_vencida,
    CASE 
        WHEN ct.total > 0 THEN 
            ROUND((COALESCE(cv.vencida, 0) / ct.total * 100)::numeric, 2)
        ELSE 0
    END as porcentaje_mora
FROM cartera_total ct
CROSS JOIN cartera_vencida cv;

-- ============================================================================
-- 4. VERIFICACIÓN DE KPIs PRINCIPALES
-- ============================================================================

-- 4.1 TOTAL PRÉSTAMOS (mes actual vs mes anterior)
WITH mes_actual AS (
    SELECT 
        COUNT(*) as cantidad,
        SUM(total_financiamiento) as monto
    FROM prestamos
    WHERE estado = 'APROBADO'
      AND DATE_TRUNC('month', fecha_aprobacion) = DATE_TRUNC('month', CURRENT_DATE)
),
mes_anterior AS (
    SELECT 
        COUNT(*) as cantidad,
        SUM(total_financiamiento) as monto
    FROM prestamos
    WHERE estado = 'APROBADO'
      AND DATE_TRUNC('month', fecha_aprobacion) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
)
SELECT 
    'TOTAL PRESTAMOS' as kpi,
    ma.cantidad as mes_actual_cantidad,
    man.cantidad as mes_anterior_cantidad,
    ma.cantidad - COALESCE(man.cantidad, 0) as variacion_cantidad,
    ma.monto as mes_actual_monto,
    COALESCE(man.monto, 0) as mes_anterior_monto,
    ma.monto - COALESCE(man.monto, 0) as variacion_monto
FROM mes_actual ma
CROSS JOIN mes_anterior man;

-- 4.2 CRÉDITOS NUEVOS EN EL MES
SELECT 
    'CREDITOS NUEVOS MES' as kpi,
    COUNT(*) as cantidad,
    SUM(total_financiamiento) as monto_total,
    DATE_TRUNC('month', fecha_aprobacion) as mes
FROM prestamos
WHERE estado = 'APROBADO'
  AND fecha_aprobacion >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY DATE_TRUNC('month', fecha_aprobacion)
ORDER BY mes DESC;

-- 4.3 TOTAL CLIENTES (activos, finalizados, inactivos)
SELECT 
    'TOTAL CLIENTES' as kpi,
    COUNT(DISTINCT CASE WHEN estado = 'APROBADO' THEN cedula END) as clientes_activos,
    COUNT(DISTINCT CASE WHEN estado = 'FINALIZADO' THEN cedula END) as clientes_finalizados,
    COUNT(DISTINCT CASE WHEN estado NOT IN ('APROBADO', 'FINALIZADO') THEN cedula END) as clientes_inactivos,
    COUNT(DISTINCT cedula) as total_clientes
FROM prestamos;

-- 4.4 TOTAL MOROSIDAD EN DÓLARES
SELECT 
    'TOTAL MOROSIDAD' as kpi,
    COUNT(DISTINCT c.prestamo_id) as prestamos_en_mora,
    COUNT(c.id) as cuotas_en_mora,
    SUM(c.monto_cuota) as monto_morosidad_total,
    AVG(CURRENT_DATE - c.fecha_vencimiento) as dias_promedio_mora
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.fecha_vencimiento < CURRENT_DATE
  AND c.estado != 'PAGADO'
  AND p.estado = 'APROBADO';

-- ============================================================================
-- 5. VERIFICACIÓN DE FINANCIAMIENTO TENDENCIA MENSUAL
-- ============================================================================

-- 5.1 Primera fecha disponible (para comparar con el error datetime vs date)
SELECT 
    'PRIMERA FECHA APROBACION' as tipo,
    MIN(fecha_aprobacion) as primera_fecha,
    pg_typeof(MIN(fecha_aprobacion)) as tipo_dato
FROM prestamos
WHERE estado = 'APROBADO'
  AND EXTRACT(YEAR FROM fecha_aprobacion) >= 2024
UNION ALL
SELECT 
    'PRIMERA FECHA CUOTA' as tipo,
    MIN(fecha_vencimiento) as primera_fecha,
    pg_typeof(MIN(fecha_vencimiento)) as tipo_dato
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND EXTRACT(YEAR FROM fecha_vencimiento) >= 2024
UNION ALL
SELECT 
    'PRIMERA FECHA PAGO' as tipo,
    MIN(fecha_pago) as primera_fecha,
    pg_typeof(MIN(fecha_pago)) as tipo_dato
FROM pagos
WHERE activo = true
  AND monto_pagado > 0
  AND EXTRACT(YEAR FROM fecha_pago) >= 2024;

-- 5.2 Nuevos financiamientos por mes (últimos 12 meses)
SELECT 
    TO_CHAR(DATE_TRUNC('month', fecha_aprobacion), 'YYYY-MM') as mes,
    COUNT(*) as cantidad_nuevos,
    SUM(total_financiamiento) as monto_nuevos,
    SUM(total_financiamiento) as total_acumulado
FROM prestamos
WHERE estado = 'APROBADO'
  AND fecha_aprobacion >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', fecha_aprobacion)
ORDER BY mes DESC;

-- 5.3 Cuotas programadas por mes (por fecha de vencimiento)
SELECT 
    TO_CHAR(DATE_TRUNC('month', c.fecha_vencimiento), 'YYYY-MM') as mes,
    COUNT(c.id) as cantidad_cuotas,
    SUM(c.monto_cuota) as monto_cuotas_programadas
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
GROUP BY DATE_TRUNC('month', c.fecha_vencimiento)
ORDER BY mes DESC;

-- 5.4 Pagos por mes (agrupados por fecha de vencimiento de la cuota)
-- NOTA: La relación se hace por prestamo_id y numero_cuota, no por cuota_id
SELECT 
    TO_CHAR(DATE_TRUNC('month', c.fecha_vencimiento), 'YYYY-MM') as mes,
    COUNT(DISTINCT pa.id) as cantidad_pagos,
    SUM(pa.monto_pagado) as monto_pagado
FROM pagos pa
INNER JOIN prestamos p ON pa.prestamo_id = p.id
INNER JOIN cuotas c ON c.prestamo_id = p.id 
    AND c.numero_cuota = pa.numero_cuota
WHERE pa.activo = true
  AND p.estado = 'APROBADO'
  AND pa.prestamo_id IS NOT NULL
  AND pa.numero_cuota IS NOT NULL
  AND c.fecha_vencimiento >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
GROUP BY DATE_TRUNC('month', c.fecha_vencimiento)
ORDER BY mes DESC;

-- 5.5 Morosidad mensual (NO acumulativa) - Comparar con endpoint
-- NOTA: La relación se hace por prestamo_id y numero_cuota
SELECT 
    TO_CHAR(DATE_TRUNC('month', c.fecha_vencimiento), 'YYYY-MM') as mes,
    SUM(c.monto_cuota) as monto_programado,
    COALESCE(SUM(pa.monto_pagado), 0) as monto_pagado,
    SUM(c.monto_cuota) - COALESCE(SUM(pa.monto_pagado), 0) as morosidad_mensual
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
LEFT JOIN pagos pa ON pa.prestamo_id = c.prestamo_id 
    AND pa.numero_cuota = c.numero_cuota 
    AND pa.activo = true
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento < CURRENT_DATE
  AND c.estado != 'PAGADO'
  AND c.fecha_vencimiento >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
GROUP BY DATE_TRUNC('month', c.fecha_vencimiento)
ORDER BY mes DESC;

-- ============================================================================
-- 6. VERIFICACIÓN DE INCONSISTENCIAS EN FECHAS (PROBLEMA DATETIME VS DATE)
-- ============================================================================

-- 6.1 Verificar si hay fechas con hora (datetime) vs solo fecha (date)
SELECT 
    'prestamos.fecha_aprobacion' as columna,
    COUNT(*) as total,
    COUNT(CASE WHEN fecha_aprobacion::time != '00:00:00' THEN 1 END) as con_hora,
    COUNT(CASE WHEN fecha_aprobacion::time = '00:00:00' THEN 1 END) as sin_hora,
    MIN(fecha_aprobacion) as ejemplo_min,
    MAX(fecha_aprobacion) as ejemplo_max
FROM prestamos
WHERE fecha_aprobacion IS NOT NULL
UNION ALL
SELECT 
    'pagos.fecha_pago' as columna,
    COUNT(*) as total,
    COUNT(CASE WHEN fecha_pago::time != '00:00:00' THEN 1 END) as con_hora,
    COUNT(CASE WHEN fecha_pago::time = '00:00:00' THEN 1 END) as sin_hora,
    MIN(fecha_pago) as ejemplo_min,
    MAX(fecha_pago) as ejemplo_max
FROM pagos
WHERE fecha_pago IS NOT NULL;

-- 6.2 Comparar tipos de datos entre tablas (para detectar incompatibilidades)
SELECT 
    'prestamos.fecha_aprobacion' as columna,
    pg_typeof(fecha_aprobacion) as tipo_dato,
    COUNT(*) as cantidad
FROM prestamos
WHERE fecha_aprobacion IS NOT NULL
GROUP BY pg_typeof(fecha_aprobacion)
UNION ALL
SELECT 
    'cuotas.fecha_vencimiento' as columna,
    pg_typeof(fecha_vencimiento) as tipo_dato,
    COUNT(*) as cantidad
FROM cuotas
WHERE fecha_vencimiento IS NOT NULL
GROUP BY pg_typeof(fecha_vencimiento)
UNION ALL
SELECT 
    'pagos.fecha_pago' as columna,
    pg_typeof(fecha_pago) as tipo_dato,
    COUNT(*) as cantidad
FROM pagos
WHERE fecha_pago IS NOT NULL
GROUP BY pg_typeof(fecha_pago);

-- ============================================================================
-- 7. VERIFICACIÓN DE PAGOS Y SU RELACIÓN CON CUOTAS
-- ============================================================================

-- 7.1 Pagos totales vs monto de cuotas
-- NOTA: La relación se hace por prestamo_id y numero_cuota
SELECT 
    'PAGOS VS CUOTAS' as verificacion,
    COUNT(DISTINCT c.id) as total_cuotas,
    COUNT(DISTINCT pa.id) as total_pagos,
    SUM(c.monto_cuota) as monto_total_cuotas,
    SUM(pa.monto_pagado) as monto_total_pagado,
    SUM(c.monto_cuota) - COALESCE(SUM(pa.monto_pagado), 0) as diferencia
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
LEFT JOIN pagos pa ON pa.prestamo_id = c.prestamo_id 
    AND pa.numero_cuota = c.numero_cuota 
    AND pa.activo = true
WHERE p.estado = 'APROBADO';

-- 7.2 Cuotas marcadas como PAGADO pero sin pagos registrados
-- NOTA: La relación se hace por prestamo_id y numero_cuota
SELECT 
    'CUOTAS PAGADAS SIN PAGOS' as problema,
    COUNT(*) as cantidad,
    SUM(monto_cuota) as monto_total
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
LEFT JOIN pagos pa ON pa.prestamo_id = c.prestamo_id 
    AND pa.numero_cuota = c.numero_cuota 
    AND pa.activo = true
WHERE c.estado = 'PAGADO'
  AND p.estado = 'APROBADO'
  AND pa.id IS NULL;

-- 7.3 Cuotas con pagos pero marcadas como NO PAGADO
-- NOTA: La relación se hace por prestamo_id y numero_cuota
SELECT 
    'CUOTAS CON PAGOS NO MARCADAS' as problema,
    COUNT(*) as cantidad,
    SUM(c.monto_cuota) as monto_cuota,
    SUM(pa.monto_pagado) as monto_pagado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
INNER JOIN pagos pa ON pa.prestamo_id = c.prestamo_id 
    AND pa.numero_cuota = c.numero_cuota 
    AND pa.activo = true
WHERE c.estado != 'PAGADO'
  AND p.estado = 'APROBADO'
  AND pa.monto_pagado >= c.monto_cuota;

-- ============================================================================
-- 8. VERIFICACIÓN DE FILTROS (ANALISTA, CONCESIONARIO, MODELO)
-- ============================================================================

-- 8.1 Valores únicos de analista
SELECT 
    'ANALISTAS' as filtro,
    COUNT(DISTINCT analista) as cantidad_distintos,
    COUNT(DISTINCT producto_financiero) as productos_distintos,
    STRING_AGG(DISTINCT analista, ', ' ORDER BY analista) as lista_analistas
FROM prestamos
WHERE estado = 'APROBADO'
  AND analista IS NOT NULL;

-- 8.2 Valores únicos de concesionario
SELECT 
    'CONCESIONARIOS' as filtro,
    COUNT(DISTINCT concesionario) as cantidad_distintos,
    STRING_AGG(DISTINCT concesionario, ', ' ORDER BY concesionario) as lista_concesionarios
FROM prestamos
WHERE estado = 'APROBADO'
  AND concesionario IS NOT NULL;

-- 8.3 Valores únicos de modelo
SELECT 
    'MODELOS' as filtro,
    COUNT(DISTINCT modelo_vehiculo) as cantidad_distintos,
    STRING_AGG(DISTINCT modelo_vehiculo, ', ' ORDER BY modelo_vehiculo) as lista_modelos
FROM prestamos
WHERE estado = 'APROBADO'
  AND modelo_vehiculo IS NOT NULL;

-- ============================================================================
-- 9. VERIFICACIÓN DE RENDIMIENTO (QUERIES LENTAS)
-- ============================================================================

-- 9.1 Índices existentes en tablas críticas
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('prestamos', 'cuotas', 'pagos')
ORDER BY tablename, indexname;

-- 9.2 Tamaño de tablas
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE tablename IN ('prestamos', 'cuotas', 'pagos')
ORDER BY size_bytes DESC;

-- 9.3 Conteo de registros por tabla
SELECT 
    'prestamos' as tabla,
    COUNT(*) as total_registros,
    COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) as aprobados
FROM prestamos
UNION ALL
SELECT 
    'cuotas' as tabla,
    COUNT(*) as total_registros,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) as pagadas
FROM cuotas
UNION ALL
SELECT 
    'pagos' as tabla,
    COUNT(*) as total_registros,
    COUNT(CASE WHEN activo = true THEN 1 END) as activos
FROM pagos;

-- ============================================================================
-- 10. RESUMEN EJECUTIVO - TODAS LAS MÉTRICAS EN UNA VISTA
-- ============================================================================

SELECT 
    '=== RESUMEN EJECUTIVO DASHBOARD ===' as seccion,
    '' as metrica,
    '' as valor;

-- Métricas principales
WITH 
cartera_total AS (
    SELECT SUM(total_financiamiento) as total FROM prestamos WHERE estado = 'APROBADO'
),
cartera_vencida AS (
    SELECT SUM(c.monto_cuota) as vencida
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE c.fecha_vencimiento < CURRENT_DATE
      AND c.estado != 'PAGADO'
      AND p.estado = 'APROBADO'
),
prestamos_mes AS (
    SELECT COUNT(*) as cantidad, SUM(total_financiamiento) as monto
    FROM prestamos
    WHERE estado = 'APROBADO'
      AND DATE_TRUNC('month', fecha_aprobacion) = DATE_TRUNC('month', CURRENT_DATE)
),
clientes_activos AS (
    SELECT COUNT(DISTINCT cedula) as cantidad
    FROM prestamos
    WHERE estado = 'APROBADO'
),
morosidad_total AS (
    SELECT SUM(c.monto_cuota) as monto
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE c.fecha_vencimiento < CURRENT_DATE
      AND c.estado != 'PAGADO'
      AND p.estado = 'APROBADO'
)
SELECT 
    'Cartera Total' as metrica,
    TO_CHAR(ct.total, 'FM$999,999,999,999.00') as valor
FROM cartera_total ct
UNION ALL
SELECT 
    'Cartera Vencida' as metrica,
    TO_CHAR(COALESCE(cv.vencida, 0), 'FM$999,999,999,999.00') as valor
FROM cartera_vencida cv
UNION ALL
SELECT 
    'Cartera al Día' as metrica,
    TO_CHAR(ct.total - COALESCE(cv.vencida, 0), 'FM$999,999,999,999.00') as valor
FROM cartera_total ct, cartera_vencida cv
UNION ALL
SELECT 
    'Porcentaje Mora' as metrica,
    CASE 
        WHEN ct.total > 0 THEN 
            ROUND((COALESCE(cv.vencida, 0) / ct.total * 100)::numeric, 2)::text || '%'
        ELSE '0%'
    END as valor
FROM cartera_total ct, cartera_vencida cv
UNION ALL
SELECT 
    'Préstamos Mes Actual' as metrica,
    pm.cantidad::text || ' ($' || TO_CHAR(pm.monto, 'FM999,999,999.00') || ')' as valor
FROM prestamos_mes pm
UNION ALL
SELECT 
    'Clientes Activos' as metrica,
    ca.cantidad::text as valor
FROM clientes_activos ca
UNION ALL
SELECT 
    'Morosidad Total' as metrica,
    TO_CHAR(COALESCE(mt.monto, 0), 'FM$999,999,999,999.00') as valor
FROM morosidad_total mt;

-- ============================================================================
-- FIN DE INVESTIGACIÓN
-- ============================================================================
-- INSTRUCCIONES:
-- 1. Ejecutar cada sección en DBeaver
-- 2. Comparar resultados con los valores del dashboard
-- 3. Identificar discrepancias
-- 4. Verificar tipos de datos (datetime vs date)
-- 5. Revisar integridad referencial
-- ============================================================================

