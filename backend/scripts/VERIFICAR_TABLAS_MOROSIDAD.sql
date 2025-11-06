-- ============================================================================
-- VERIFICACIÓN: DÓNDE SE ENCUENTRAN LAS MÉTRICAS DE MOROSIDAD
-- ============================================================================
-- Este script verifica si existen tablas oficiales de morosidad
-- y cómo se calculan las métricas
-- ============================================================================

-- ============================================================================
-- 1. VERIFICAR SI EXISTEN TABLAS OFICIALES DE MOROSIDAD
-- ============================================================================
SELECT 
    '=== TABLAS OFICIALES DE MOROSIDAD ===' AS verificacion,
    table_name,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = table_name
        ) THEN '✅ EXISTE'
        ELSE '❌ NO EXISTE'
    END AS existe
FROM (VALUES 
    ('dashboard_morosidad_mensual'),
    ('dashboard_morosidad_por_analista')
) AS tablas(table_name);

-- ============================================================================
-- 2. VERIFICAR ESTRUCTURA DE dashboard_morosidad_mensual (SI EXISTE)
-- ============================================================================
SELECT 
    '=== ESTRUCTURA: dashboard_morosidad_mensual ===' AS verificacion,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'dashboard_morosidad_mensual'
ORDER BY ordinal_position;

-- ============================================================================
-- 3. VERIFICAR DATOS EN dashboard_morosidad_mensual (SI EXISTE)
-- ============================================================================
SELECT 
    '=== DATOS EN dashboard_morosidad_mensual ===' AS verificacion,
    COUNT(*) AS total_registros,
    MIN(año || '-' || LPAD(mes::text, 2, '0')) AS mes_mas_antiguo,
    MAX(año || '-' || LPAD(mes::text, 2, '0')) AS mes_mas_reciente,
    SUM(morosidad_total) AS total_morosidad_acumulada,
    MAX(fecha_actualizacion) AS ultima_actualizacion
FROM dashboard_morosidad_mensual;

-- ============================================================================
-- 4. MUESTRA DE DATOS DE dashboard_morosidad_mensual (ÚLTIMOS 6 MESES)
-- ============================================================================
SELECT 
    '=== MUESTRA: ÚLTIMOS 6 MESES ===' AS verificacion,
    año,
    mes,
    TO_CHAR(año || '-' || LPAD(mes::text, 2, '0'), 'Mon YYYY') AS mes_formateado,
    morosidad_total,
    TO_CHAR(morosidad_total, 'FM$999,999,999,990.00') AS morosidad_formateada,
    cantidad_cuotas_vencidas,
    cantidad_prestamos_afectados,
    fecha_actualizacion
FROM dashboard_morosidad_mensual
ORDER BY año DESC, mes DESC
LIMIT 6;

-- ============================================================================
-- 5. VERIFICAR ESTRUCTURA DE dashboard_morosidad_por_analista (SI EXISTE)
-- ============================================================================
SELECT 
    '=== ESTRUCTURA: dashboard_morosidad_por_analista ===' AS verificacion,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'dashboard_morosidad_por_analista'
ORDER BY ordinal_position;

-- ============================================================================
-- 6. VERIFICAR DATOS EN dashboard_morosidad_por_analista (SI EXISTE)
-- ============================================================================
SELECT 
    '=== DATOS EN dashboard_morosidad_por_analista ===' AS verificacion,
    COUNT(*) AS total_analistas,
    SUM(total_morosidad) AS total_morosidad_acumulada,
    AVG(promedio_morosidad_por_cliente)::NUMERIC(10,2) AS promedio_general
FROM dashboard_morosidad_por_analista;

-- ============================================================================
-- 7. COMPARAR: TABLA OFICIAL vs CÁLCULO EN TIEMPO REAL
-- ============================================================================
-- Calcular morosidad actual desde las tablas base (cuotas + prestamos)
WITH morosidad_calculada AS (
    SELECT 
        EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
        EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
        COALESCE(SUM(c.monto_cuota), 0) as morosidad_calculada,
        COUNT(*) as cuotas_calculadas
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE 
        p.estado = 'APROBADO'
        AND c.fecha_vencimiento < CURRENT_DATE
        AND c.estado != 'PAGADO'
        AND EXTRACT(YEAR FROM c.fecha_vencimiento) >= EXTRACT(YEAR FROM CURRENT_DATE) - 1
    GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
)
SELECT 
    '=== COMPARACIÓN: TABLA OFICIAL vs CÁLCULO REAL ===' AS verificacion,
    COALESCE(d.año, m.año) AS año,
    COALESCE(d.mes, m.mes) AS mes,
    d.morosidad_total AS morosidad_tabla_oficial,
    m.morosidad_calculada AS morosidad_calculo_real,
    (d.morosidad_total - m.morosidad_calculada) AS diferencia,
    CASE 
        WHEN ABS(d.morosidad_total - m.morosidad_calculada) < 0.01 THEN '✅ COINCIDEN'
        ELSE '⚠️ DIFERENCIAS'
    END AS estado
FROM dashboard_morosidad_mensual d
FULL OUTER JOIN morosidad_calculada m ON (d.año = m.año AND d.mes = m.mes)
WHERE COALESCE(d.año, m.año) >= EXTRACT(YEAR FROM CURRENT_DATE) - 1
ORDER BY COALESCE(d.año, m.año) DESC, COALESCE(d.mes, m.mes) DESC
LIMIT 6;

-- ============================================================================
-- 8. RESUMEN: DÓNDE SE ENCUENTRAN LAS MÉTRICAS
-- ============================================================================
SELECT 
    '=== RESUMEN: DÓNDE SE ENCUENTRAN LAS MÉTRICAS ===' AS verificacion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'dashboard_morosidad_mensual'
        ) THEN 
            '✅ Tabla oficial existe: dashboard_morosidad_mensual'
        ELSE 
            '❌ Tabla oficial NO existe: Se calcula en tiempo real'
    END AS estado_tabla_oficial,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'dashboard_morosidad_mensual'
        ) THEN 
            '✅ Los endpoints usan la tabla oficial (más rápido)'
        ELSE 
            '⚠️ Los endpoints calculan en tiempo real desde cuotas + prestamos (más lento)'
    END AS como_se_calcula,
    '📊 Métricas detalladas: Usa el script CALCULAR_MOROSIDAD_KPIS.sql' AS recomendacion;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

