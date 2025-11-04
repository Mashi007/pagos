-- ============================================================================
-- SCRIPT PARA ACTUALIZAR TODAS LAS TABLAS OFICIALES DEL DASHBOARD
-- ============================================================================
-- Este script actualiza todas las tablas oficiales con datos actuales
-- Ejecutar periódicamente (diariamente o cuando se necesite actualizar)
-- ============================================================================

-- ============================================================================
-- 1. ACTUALIZAR dashboard_morosidad_mensual
-- ============================================================================

INSERT INTO dashboard_morosidad_mensual (año, mes, morosidad_total, cantidad_cuotas_vencidas, cantidad_prestamos_afectados)
SELECT 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad_total,
    COUNT(c.id) as cantidad_cuotas_vencidas,
    COUNT(DISTINCT p.id) as cantidad_prestamos_afectados
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento < CURRENT_DATE
    AND c.estado != 'PAGADO'
GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
ON CONFLICT (año, mes) DO UPDATE SET
    morosidad_total = EXCLUDED.morosidad_total,
    cantidad_cuotas_vencidas = EXCLUDED.cantidad_cuotas_vencidas,
    cantidad_prestamos_afectados = EXCLUDED.cantidad_prestamos_afectados,
    fecha_actualizacion = CURRENT_TIMESTAMP;


-- ============================================================================
-- 2. ACTUALIZAR dashboard_cobranzas_mensuales
-- ============================================================================

WITH nombres_meses AS (
    SELECT 
        generate_series(1, 12) as mes_num,
        unnest(ARRAY['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']) as nombre
)
INSERT INTO dashboard_cobranzas_mensuales (año, mes, nombre_mes, cobranzas_planificadas, pagos_reales)
SELECT 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    nm.nombre as nombre_mes,
    COALESCE(SUM(c.monto_cuota), 0) as cobranzas_planificadas,
    COALESCE(SUM(ps.monto_pagado::numeric), 0) as pagos_reales
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
LEFT JOIN pagos_staging ps ON 
    EXTRACT(YEAR FROM ps.fecha_pago::timestamp) = EXTRACT(YEAR FROM c.fecha_vencimiento)
    AND EXTRACT(MONTH FROM ps.fecha_pago::timestamp) = EXTRACT(MONTH FROM c.fecha_vencimiento)
    AND ps.fecha_pago IS NOT NULL
    AND ps.fecha_pago != ''
    AND ps.fecha_pago ~ '^\\d{4}-\\d{2}-\\d{2}'
INNER JOIN nombres_meses nm ON nm.mes_num = EXTRACT(MONTH FROM c.fecha_vencimiento)::int
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento >= CURRENT_DATE - INTERVAL '12 months'
    AND c.fecha_vencimiento <= CURRENT_DATE
GROUP BY 
    EXTRACT(YEAR FROM c.fecha_vencimiento),
    EXTRACT(MONTH FROM c.fecha_vencimiento),
    nm.nombre
ON CONFLICT (año, mes) DO UPDATE SET
    cobranzas_planificadas = EXCLUDED.cobranzas_planificadas,
    pagos_reales = EXCLUDED.pagos_reales,
    fecha_actualizacion = CURRENT_TIMESTAMP;


-- ============================================================================
-- 3. ACTUALIZAR dashboard_kpis_diarios
-- ============================================================================

INSERT INTO dashboard_kpis_diarios (
    fecha,
    total_prestamos,
    total_prestamos_valor,
    creditos_nuevos_mes,
    creditos_nuevos_mes_valor,
    total_clientes,
    total_morosidad_usd,
    cartera_total,
    total_cobrado
)
SELECT 
    CURRENT_DATE as fecha,
    COUNT(DISTINCT p.id) FILTER (WHERE p.estado = 'APROBADO') as total_prestamos,
    COALESCE(SUM(p.total_financiamiento) FILTER (WHERE p.estado = 'APROBADO'), 0) as total_prestamos_valor,
    COUNT(DISTINCT p.id) FILTER (
        WHERE p.estado = 'APROBADO' 
        AND EXTRACT(YEAR FROM p.fecha_aprobacion) = EXTRACT(YEAR FROM CURRENT_DATE)
        AND EXTRACT(MONTH FROM p.fecha_aprobacion) = EXTRACT(MONTH FROM CURRENT_DATE)
    ) as creditos_nuevos_mes,
    COALESCE(SUM(p.total_financiamiento) FILTER (
        WHERE p.estado = 'APROBADO' 
        AND EXTRACT(YEAR FROM p.fecha_aprobacion) = EXTRACT(YEAR FROM CURRENT_DATE)
        AND EXTRACT(MONTH FROM p.fecha_aprobacion) = EXTRACT(MONTH FROM CURRENT_DATE)
    ), 0) as creditos_nuevos_mes_valor,
    COUNT(DISTINCT p.cedula) FILTER (WHERE p.estado = 'APROBADO') as total_clientes,
    COALESCE(SUM(c.monto_cuota) FILTER (
        WHERE c.fecha_vencimiento < CURRENT_DATE 
        AND c.estado != 'PAGADO'
    ), 0) as total_morosidad_usd,
    COALESCE(SUM(p.total_financiamiento) FILTER (WHERE p.estado = 'APROBADO'), 0) as cartera_total,
    COALESCE(SUM(ps.monto_pagado::numeric) FILTER (
        WHERE ps.fecha_pago IS NOT NULL
        AND ps.fecha_pago != ''
        AND ps.fecha_pago ~ '^\\d{4}-\\d{2}-\\d{2}'
        AND ps.fecha_pago::timestamp >= DATE_TRUNC('month', CURRENT_DATE)
        AND ps.fecha_pago::timestamp < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
    ), 0) as total_cobrado
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
LEFT JOIN pagos_staging ps ON ps.fecha_pago IS NOT NULL
WHERE p.estado = 'APROBADO'
ON CONFLICT (fecha) DO UPDATE SET
    total_prestamos = EXCLUDED.total_prestamos,
    total_prestamos_valor = EXCLUDED.total_prestamos_valor,
    creditos_nuevos_mes = EXCLUDED.creditos_nuevos_mes,
    creditos_nuevos_mes_valor = EXCLUDED.creditos_nuevos_mes_valor,
    total_clientes = EXCLUDED.total_clientes,
    total_morosidad_usd = EXCLUDED.total_morosidad_usd,
    cartera_total = EXCLUDED.cartera_total,
    total_cobrado = EXCLUDED.total_cobrado,
    fecha_actualizacion = CURRENT_TIMESTAMP;


-- ============================================================================
-- 4. ACTUALIZAR dashboard_financiamiento_mensual
-- ============================================================================

WITH nombres_meses AS (
    SELECT 
        generate_series(1, 12) as mes_num,
        unnest(ARRAY['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                     'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']) as nombre
),
prestamos_por_mes AS (
    SELECT 
        EXTRACT(YEAR FROM p.fecha_aprobacion)::int as año,
        EXTRACT(MONTH FROM p.fecha_aprobacion)::int as mes,
        COUNT(p.id) as cantidad_nuevos,
        COALESCE(SUM(p.total_financiamiento), 0) as monto_nuevos
    FROM prestamos p
    WHERE p.estado = 'APROBADO'
        AND p.fecha_aprobacion IS NOT NULL
        AND p.fecha_aprobacion >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY EXTRACT(YEAR FROM p.fecha_aprobacion), EXTRACT(MONTH FROM p.fecha_aprobacion)
)
INSERT INTO dashboard_financiamiento_mensual (año, mes, nombre_mes, cantidad_nuevos, monto_nuevos, total_acumulado)
SELECT 
    ppm.año,
    ppm.mes,
    nm.nombre as nombre_mes,
    ppm.cantidad_nuevos,
    ppm.monto_nuevos,
    SUM(ppm.monto_nuevos) OVER (ORDER BY ppm.año, ppm.mes) as total_acumulado
FROM prestamos_por_mes ppm
INNER JOIN nombres_meses nm ON nm.mes_num = ppm.mes
ON CONFLICT (año, mes) DO UPDATE SET
    cantidad_nuevos = EXCLUDED.cantidad_nuevos,
    monto_nuevos = EXCLUDED.monto_nuevos,
    total_acumulado = EXCLUDED.total_acumulado,
    fecha_actualizacion = CURRENT_TIMESTAMP;


-- ============================================================================
-- 5. ACTUALIZAR dashboard_morosidad_por_analista
-- ============================================================================

INSERT INTO dashboard_morosidad_por_analista (
    analista,
    total_morosidad,
    cantidad_clientes,
    cantidad_cuotas_atrasadas,
    promedio_morosidad_por_cliente
)
SELECT 
    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
    COALESCE(SUM(c.monto_cuota), 0) as total_morosidad,
    COUNT(DISTINCT p.cedula) as cantidad_clientes,
    COUNT(c.id) as cantidad_cuotas_atrasadas,
    CASE 
        WHEN COUNT(DISTINCT p.cedula) > 0 
        THEN COALESCE(SUM(c.monto_cuota), 0) / COUNT(DISTINCT p.cedula)
        ELSE 0
    END as promedio_morosidad_por_cliente
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento < CURRENT_DATE
    AND c.estado != 'PAGADO'
GROUP BY COALESCE(p.analista, p.producto_financiero, 'Sin Analista')
ON CONFLICT (analista) DO UPDATE SET
    total_morosidad = EXCLUDED.total_morosidad,
    cantidad_clientes = EXCLUDED.cantidad_clientes,
    cantidad_cuotas_atrasadas = EXCLUDED.cantidad_cuotas_atrasadas,
    promedio_morosidad_por_cliente = EXCLUDED.promedio_morosidad_por_cliente,
    fecha_actualizacion = CURRENT_TIMESTAMP;


-- ============================================================================
-- 6. ACTUALIZAR dashboard_prestamos_por_concesionario
-- ============================================================================

WITH total_prestamos AS (
    SELECT COUNT(*)::numeric as total
    FROM prestamos
    WHERE estado = 'APROBADO'
)
INSERT INTO dashboard_prestamos_por_concesionario (concesionario, total_prestamos, porcentaje)
SELECT 
    COALESCE(p.concesionario, 'Sin Concesionario') as concesionario,
    COUNT(p.id) as total_prestamos,
    CASE 
        WHEN tp.total > 0 
        THEN (COUNT(p.id)::numeric / tp.total * 100)
        ELSE 0
    END as porcentaje
FROM prestamos p
CROSS JOIN total_prestamos tp
WHERE p.estado = 'APROBADO'
GROUP BY COALESCE(p.concesionario, 'Sin Concesionario'), tp.total
ON CONFLICT (concesionario) DO UPDATE SET
    total_prestamos = EXCLUDED.total_prestamos,
    porcentaje = EXCLUDED.porcentaje,
    fecha_actualizacion = CURRENT_TIMESTAMP;


-- ============================================================================
-- 7. ACTUALIZAR dashboard_pagos_mensuales
-- ============================================================================

WITH nombres_meses AS (
    SELECT 
        generate_series(1, 12) as mes_num,
        unnest(ARRAY['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                     'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']) as nombre
)
INSERT INTO dashboard_pagos_mensuales (año, mes, nombre_mes, cantidad_pagos, monto_total)
SELECT 
    EXTRACT(YEAR FROM ps.fecha_pago::timestamp)::int as año,
    EXTRACT(MONTH FROM ps.fecha_pago::timestamp)::int as mes,
    nm.nombre as nombre_mes,
    COUNT(ps.id) as cantidad_pagos,
    COALESCE(SUM(ps.monto_pagado::numeric), 0) as monto_total
FROM pagos_staging ps
INNER JOIN nombres_meses nm ON nm.mes_num = EXTRACT(MONTH FROM ps.fecha_pago::timestamp)::int
WHERE 
    ps.fecha_pago IS NOT NULL
    AND ps.fecha_pago != ''
    AND ps.fecha_pago ~ '^\\d{4}-\\d{2}-\\d{2}'
    AND ps.monto_pagado IS NOT NULL
    AND ps.monto_pagado != ''
    AND ps.monto_pagado ~ '^[0-9]+(\\.[0-9]+)?$'
    AND ps.fecha_pago::timestamp >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY 
    EXTRACT(YEAR FROM ps.fecha_pago::timestamp),
    EXTRACT(MONTH FROM ps.fecha_pago::timestamp),
    nm.nombre
ON CONFLICT (año, mes) DO UPDATE SET
    cantidad_pagos = EXCLUDED.cantidad_pagos,
    monto_total = EXCLUDED.monto_total,
    fecha_actualizacion = CURRENT_TIMESTAMP;


-- ============================================================================
-- 8. ACTUALIZAR dashboard_cobros_por_analista
-- ============================================================================
-- Nota: Esta tabla requiere información de analista en pagos, 
-- lo cual puede no estar disponible directamente en pagos_staging
-- Se omite por ahora o se puede implementar con JOIN a prestamos

-- ============================================================================
-- 9. ACTUALIZAR dashboard_metricas_acumuladas
-- ============================================================================

INSERT INTO dashboard_metricas_acumuladas (
    fecha,
    cartera_total,
    morosidad_total,
    total_cobrado,
    total_prestamos,
    total_clientes
)
SELECT 
    CURRENT_DATE as fecha,
    COALESCE(SUM(p.total_financiamiento) FILTER (WHERE p.estado = 'APROBADO'), 0) as cartera_total,
    COALESCE(SUM(c.monto_cuota) FILTER (
        WHERE c.fecha_vencimiento < CURRENT_DATE 
        AND c.estado != 'PAGADO'
    ), 0) as morosidad_total,
    COALESCE(SUM(ps.monto_pagado::numeric) FILTER (
        WHERE ps.fecha_pago IS NOT NULL
        AND ps.fecha_pago != ''
        AND ps.fecha_pago ~ '^\\d{4}-\\d{2}-\\d{2}'
    ), 0) as total_cobrado,
    COUNT(DISTINCT p.id) FILTER (WHERE p.estado = 'APROBADO') as total_prestamos,
    COUNT(DISTINCT p.cedula) FILTER (WHERE p.estado = 'APROBADO') as total_clientes
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
LEFT JOIN pagos_staging ps ON ps.fecha_pago IS NOT NULL
WHERE p.estado = 'APROBADO'
ON CONFLICT (fecha) DO UPDATE SET
    cartera_total = EXCLUDED.cartera_total,
    morosidad_total = EXCLUDED.morosidad_total,
    total_cobrado = EXCLUDED.total_cobrado,
    total_prestamos = EXCLUDED.total_prestamos,
    total_clientes = EXCLUDED.total_clientes,
    fecha_actualizacion = CURRENT_TIMESTAMP;


-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

SELECT 
    'dashboard_morosidad_mensual' as tabla,
    COUNT(*) as registros,
    MAX(fecha_actualizacion) as ultima_actualizacion
FROM dashboard_morosidad_mensual
UNION ALL
SELECT 
    'dashboard_cobranzas_mensuales',
    COUNT(*),
    MAX(fecha_actualizacion)
FROM dashboard_cobranzas_mensuales
UNION ALL
SELECT 
    'dashboard_kpis_diarios',
    COUNT(*),
    MAX(fecha_actualizacion)
FROM dashboard_kpis_diarios
UNION ALL
SELECT 
    'dashboard_financiamiento_mensual',
    COUNT(*),
    MAX(fecha_actualizacion)
FROM dashboard_financiamiento_mensual
UNION ALL
SELECT 
    'dashboard_morosidad_por_analista',
    COUNT(*),
    MAX(fecha_actualizacion)
FROM dashboard_morosidad_por_analista
UNION ALL
SELECT 
    'dashboard_prestamos_por_concesionario',
    COUNT(*),
    MAX(fecha_actualizacion)
FROM dashboard_prestamos_por_concesionario
UNION ALL
SELECT 
    'dashboard_pagos_mensuales',
    COUNT(*),
    MAX(fecha_actualizacion)
FROM dashboard_pagos_mensuales
UNION ALL
SELECT 
    'dashboard_metricas_acumuladas',
    COUNT(*),
    MAX(fecha_actualizacion)
FROM dashboard_metricas_acumuladas;

