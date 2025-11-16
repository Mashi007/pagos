-- ============================================
-- Script para verificar tablas de Machine Learning
-- Ejecutar en DBeaver o cualquier cliente SQL
-- ============================================

-- ============================================
-- 1. VERIFICAR TABLA: modelos_riesgo
-- ============================================

-- 1.1 Verificar si la tabla existe
SELECT 
    table_name,
    table_schema
FROM 
    information_schema.tables 
WHERE 
    table_name = 'modelos_riesgo';

-- 1.2 Verificar estructura de la tabla modelos_riesgo
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM 
    information_schema.columns
WHERE 
    table_name = 'modelos_riesgo'
ORDER BY 
    ordinal_position;

-- 1.3 Verificar índices de modelos_riesgo
SELECT 
    indexname,
    indexdef
FROM 
    pg_indexes
WHERE 
    tablename = 'modelos_riesgo';

-- 1.4 Contar modelos de riesgo
SELECT 
    COUNT(*) as total_modelos,
    COUNT(*) FILTER (WHERE activo = true) as modelos_activos,
    COUNT(*) FILTER (WHERE activo = false) as modelos_inactivos,
    MIN(entrenado_en) as primer_entrenamiento,
    MAX(entrenado_en) as ultimo_entrenamiento
FROM 
    modelos_riesgo;

-- 1.5 Ver modelos de riesgo disponibles
SELECT 
    id,
    nombre,
    version,
    algoritmo,
    accuracy,
    activo,
    entrenado_en,
    ruta_archivo
FROM 
    modelos_riesgo
ORDER BY 
    entrenado_en DESC
LIMIT 10;

-- ============================================
-- 2. VERIFICAR TABLA: modelos_impago_cuotas
-- ============================================

-- 2.1 Verificar si la tabla existe
SELECT 
    table_name,
    table_schema
FROM 
    information_schema.tables 
WHERE 
    table_name = 'modelos_impago_cuotas';

-- 2.2 Verificar estructura de la tabla modelos_impago_cuotas
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM 
    information_schema.columns
WHERE 
    table_name = 'modelos_impago_cuotas'
ORDER BY 
    ordinal_position;

-- 2.3 Verificar índices de modelos_impago_cuotas
SELECT 
    indexname,
    indexdef
FROM 
    pg_indexes
WHERE 
    tablename = 'modelos_impago_cuotas';

-- 2.4 Contar modelos de impago
SELECT 
    COUNT(*) as total_modelos,
    COUNT(*) FILTER (WHERE activo = true) as modelos_activos,
    COUNT(*) FILTER (WHERE activo = false) as modelos_inactivos,
    MIN(entrenado_en) as primer_entrenamiento,
    MAX(entrenado_en) as ultimo_entrenamiento
FROM 
    modelos_impago_cuotas;

-- 2.5 Ver modelos de impago disponibles
SELECT 
    id,
    nombre,
    version,
    algoritmo,
    accuracy,
    activo,
    entrenado_en,
    ruta_archivo
FROM 
    modelos_impago_cuotas
ORDER BY 
    entrenado_en DESC
LIMIT 10;

-- ============================================
-- 3. VERIFICAR DATOS PARA ENTRENAMIENTO
-- ============================================

-- 3.1 Verificar préstamos aprobados (para ML Riesgo)
SELECT 
    COUNT(*) as total_prestamos_aprobados,
    COUNT(*) FILTER (WHERE fecha_aprobacion IS NOT NULL) as con_fecha_aprobacion,
    COUNT(DISTINCT cliente_id) as clientes_unicos
FROM 
    prestamos
WHERE 
    estado = 'APROBADO';

-- 3.2 Verificar préstamos con cuotas (para ML Impago)
SELECT 
    COUNT(DISTINCT p.id) as prestamos_con_cuotas,
    COUNT(c.id) as total_cuotas,
    AVG(cuotas_por_prestamo.cantidad) as promedio_cuotas_por_prestamo
FROM 
    prestamos p
    INNER JOIN (
        SELECT prestamo_id, COUNT(*) as cantidad
        FROM cuotas
        GROUP BY prestamo_id
        HAVING COUNT(*) >= 2
    ) cuotas_por_prestamo ON p.id = cuotas_por_prestamo.prestamo_id
    INNER JOIN cuotas c ON p.id = c.prestamo_id
WHERE 
    p.estado = 'APROBADO'
    AND p.fecha_aprobacion IS NOT NULL;

-- 3.3 Verificar préstamos con historial de pagos
SELECT 
    COUNT(DISTINCT p.id) as prestamos_con_pagos,
    COUNT(pa.id) as total_pagos,
    SUM(pa.monto_pagado) as monto_total_pagado
FROM 
    prestamos p
    LEFT JOIN pagos pa ON p.id = pa.prestamo_id
WHERE 
    p.estado = 'APROBADO';

-- 3.4 Verificar cuotas vencidas (para determinar targets)
SELECT 
    COUNT(*) as total_cuotas_vencidas,
    COUNT(*) FILTER (WHERE estado = 'PAGADA') as cuotas_pagadas,
    COUNT(*) FILTER (WHERE estado NOT IN ('PAGADA', 'PARCIAL')) as cuotas_sin_pagar,
    COUNT(DISTINCT prestamo_id) as prestamos_con_cuotas_vencidas
FROM 
    cuotas
WHERE 
    fecha_vencimiento < CURRENT_DATE;

-- ============================================
-- 4. RESUMEN COMPLETO
-- ============================================

SELECT 
    'modelos_riesgo' as tabla,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'modelos_riesgo'
        ) THEN '✅ EXISTE'
        ELSE '❌ NO EXISTE'
    END as estado,
    (SELECT COUNT(*) FROM modelos_riesgo) as total_registros,
    (SELECT COUNT(*) FROM modelos_riesgo WHERE activo = true) as modelos_activos
UNION ALL
SELECT 
    'modelos_impago_cuotas' as tabla,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'modelos_impago_cuotas'
        ) THEN '✅ EXISTE'
        ELSE '❌ NO EXISTE'
    END as estado,
    (SELECT COUNT(*) FROM modelos_impago_cuotas) as total_registros,
    (SELECT COUNT(*) FROM modelos_impago_cuotas WHERE activo = true) as modelos_activos;

-- ============================================
-- 5. VERIFICAR DATOS MÍNIMOS PARA ENTRENAR
-- ============================================

-- 5.1 Verificar datos para ML Riesgo (mínimo 10 préstamos)
SELECT 
    'ML Riesgo' as modelo,
    COUNT(*) as prestamos_disponibles,
    CASE 
        WHEN COUNT(*) >= 10 THEN '✅ SUFICIENTES'
        ELSE '❌ INSUFICIENTES (mínimo 10)'
    END as estado
FROM 
    prestamos
WHERE 
    estado = 'APROBADO';

-- 5.2 Verificar datos para ML Impago (mínimo 10 préstamos con cuotas)
SELECT 
    'ML Impago' as modelo,
    COUNT(DISTINCT p.id) as prestamos_con_cuotas,
    CASE 
        WHEN COUNT(DISTINCT p.id) >= 10 THEN '✅ SUFICIENTES'
        ELSE '❌ INSUFICIENTES (mínimo 10)'
    END as estado
FROM 
    prestamos p
    INNER JOIN cuotas c ON p.id = c.prestamo_id
WHERE 
    p.estado = 'APROBADO'
    AND p.fecha_aprobacion IS NOT NULL
    AND (
        SELECT COUNT(*) 
        FROM cuotas c2 
        WHERE c2.prestamo_id = p.id
    ) >= 2;

-- ============================================
-- 6. VERIFICAR MODELOS ACTIVOS
-- ============================================

-- 6.1 Modelo activo de riesgo
SELECT 
    id,
    nombre,
    algoritmo,
    accuracy,
    precision,
    recall,
    f1_score,
    entrenado_en,
    ruta_archivo
FROM 
    modelos_riesgo
WHERE 
    activo = true
LIMIT 1;

-- 6.2 Modelo activo de impago
SELECT 
    id,
    nombre,
    algoritmo,
    accuracy,
    precision,
    recall,
    f1_score,
    entrenado_en,
    ruta_archivo
FROM 
    modelos_impago_cuotas
WHERE 
    activo = true
LIMIT 1;

-- ============================================
-- 7. VERIFICAR MÉTRICAS DE MODELOS
-- ============================================

-- 7.1 Estadísticas de modelos de riesgo
SELECT 
    algoritmo,
    COUNT(*) as cantidad,
    AVG(accuracy) as accuracy_promedio,
    AVG(precision) as precision_promedio,
    AVG(recall) as recall_promedio,
    AVG(f1_score) as f1_promedio,
    MAX(entrenado_en) as ultimo_entrenamiento
FROM 
    modelos_riesgo
GROUP BY 
    algoritmo
ORDER BY 
    cantidad DESC;

-- 7.2 Estadísticas de modelos de impago
SELECT 
    algoritmo,
    COUNT(*) as cantidad,
    AVG(accuracy) as accuracy_promedio,
    AVG(precision) as precision_promedio,
    AVG(recall) as recall_promedio,
    AVG(f1_score) as f1_promedio,
    MAX(entrenado_en) as ultimo_entrenamiento
FROM 
    modelos_impago_cuotas
GROUP BY 
    algoritmo
ORDER BY 
    cantidad DESC;

-- ============================================
-- 8. ANÁLISIS DE RIESGO POR CLIENTE (ML IMPAGO)
-- ============================================

-- 8.1 Features de ML Impago por Préstamo
-- Calcula todas las features que usa el modelo de ML impago para cada préstamo
SELECT 
    p.id as prestamo_id,
    c.id as cliente_id,
    c.cedula,
    c.nombre || ' ' || c.apellido as nombre_cliente,
    p.total_financiamiento,
    p.fecha_aprobacion,
    -- Features del modelo ML Impago
    -- Porcentaje de cuotas pagadas
    CASE 
        WHEN COUNT(cu.id) > 0 THEN 
            (COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END)::numeric / COUNT(cu.id)::numeric * 100)
        ELSE 0 
    END as porcentaje_cuotas_pagadas,
    -- Promedio de días de mora
    COALESCE(AVG(CASE WHEN cu.dias_mora > 0 THEN cu.dias_mora END), 0) as promedio_dias_mora,
    -- Número de cuotas atrasadas
    COUNT(CASE WHEN cu.estado = 'ATRASADO' THEN 1 END) as numero_cuotas_atrasadas,
    -- Número de cuotas parciales
    COUNT(CASE WHEN cu.estado = 'PARCIAL' THEN 1 END) as numero_cuotas_parciales,
    -- Tasa de cumplimiento (cuotas pagadas a tiempo / total cuotas vencidas)
    CASE 
        WHEN COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE THEN 1 END) > 0 THEN
            (COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado = 'PAGADO' THEN 1 END)::numeric / 
             COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE THEN 1 END)::numeric * 100)
        ELSE 100 
    END as tasa_cumplimiento,
    -- Días desde último pago
    COALESCE(MAX(CASE WHEN cu.fecha_pago IS NOT NULL THEN (CURRENT_DATE - cu.fecha_pago) END), 
             CASE WHEN p.fecha_aprobacion IS NOT NULL THEN (CURRENT_DATE - p.fecha_aprobacion) ELSE 0 END) as dias_desde_ultimo_pago,
    -- Número de cuotas restantes
    COUNT(CASE WHEN cu.fecha_vencimiento > CURRENT_DATE OR cu.estado = 'PENDIENTE' THEN 1 END) as numero_cuotas_restantes,
    -- Monto promedio de cuota
    COALESCE(AVG(cu.monto_cuota), 0) as monto_promedio_cuota,
    -- Ratio de monto pendiente
    CASE 
        WHEN p.total_financiamiento > 0 THEN
            ((p.total_financiamiento - COALESCE(SUM(cu.total_pagado), 0)) / p.total_financiamiento * 100)
        ELSE 0 
    END as ratio_monto_pendiente,
    -- Cuotas vencidas sin pagar
    COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado NOT IN ('PAGADO', 'PARCIAL') THEN 1 END) as cuotas_vencidas_sin_pagar,
    -- Monto total pendiente
    (p.total_financiamiento - COALESCE(SUM(cu.total_pagado), 0)) as monto_total_pendiente,
    -- Total de cuotas
    COUNT(cu.id) as total_cuotas
FROM 
    prestamos p
    INNER JOIN clientes c ON p.cliente_id = c.id
    LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE 
    p.estado = 'APROBADO'
    AND p.fecha_aprobacion IS NOT NULL
GROUP BY 
    p.id, c.id, c.cedula, c.nombre, c.apellido, p.total_financiamiento, p.fecha_aprobacion
HAVING 
    COUNT(cu.id) >= 2  -- Al menos 2 cuotas para análisis válido
ORDER BY 
    cuotas_vencidas_sin_pagar DESC, ratio_monto_pendiente DESC;

-- 8.2 Análisis de Riesgo por Cliente (Resumen)
-- Agrupa el análisis de riesgo por cliente, mostrando el peor caso
SELECT 
    c.id as cliente_id,
    c.cedula,
    c.nombre || ' ' || c.apellido as nombre_cliente,
    COUNT(DISTINCT p.id) as total_prestamos,
    -- Métricas consolidadas del cliente
    AVG(porcentaje_cuotas_pagadas) as porcentaje_cuotas_pagadas_promedio,
    MAX(promedio_dias_mora) as max_dias_mora,
    SUM(numero_cuotas_atrasadas) as total_cuotas_atrasadas,
    SUM(cuotas_vencidas_sin_pagar) as total_cuotas_vencidas_sin_pagar,
    AVG(tasa_cumplimiento) as tasa_cumplimiento_promedio,
    MAX(dias_desde_ultimo_pago) as max_dias_sin_pago,
    SUM(monto_total_pendiente) as monto_total_pendiente_cliente,
    -- Clasificación de riesgo basada en features
    CASE 
        WHEN SUM(cuotas_vencidas_sin_pagar) > 3 OR AVG(tasa_cumplimiento) < 50 THEN 'ALTO RIESGO'
        WHEN SUM(cuotas_vencidas_sin_pagar) > 0 OR AVG(tasa_cumplimiento) < 70 THEN 'MEDIO RIESGO'
        WHEN AVG(porcentaje_cuotas_pagadas) >= 80 AND AVG(tasa_cumplimiento) >= 90 THEN 'BAJO RIESGO'
        ELSE 'RIESGO MODERADO'
    END as nivel_riesgo_estimado
FROM 
    clientes c
    INNER JOIN prestamos p ON c.id = p.cliente_id
    INNER JOIN (
        SELECT 
            p.id as prestamo_id,
            p.cliente_id,
            -- Features calculadas
            CASE 
                WHEN COUNT(cu.id) > 0 THEN 
                    (COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END)::numeric / COUNT(cu.id)::numeric * 100)
                ELSE 0 
            END as porcentaje_cuotas_pagadas,
            COALESCE(AVG(CASE WHEN cu.dias_mora > 0 THEN cu.dias_mora END), 0) as promedio_dias_mora,
            COUNT(CASE WHEN cu.estado = 'ATRASADO' THEN 1 END) as numero_cuotas_atrasadas,
            CASE 
                WHEN COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE THEN 1 END) > 0 THEN
                    (COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado = 'PAGADO' THEN 1 END)::numeric / 
                     COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE THEN 1 END)::numeric * 100)
                ELSE 100 
            END as tasa_cumplimiento,
            COALESCE(MAX(CASE WHEN cu.fecha_pago IS NOT NULL THEN (CURRENT_DATE - cu.fecha_pago) END), 
                     CASE WHEN p.fecha_aprobacion IS NOT NULL THEN (CURRENT_DATE - p.fecha_aprobacion) ELSE 0 END) as dias_desde_ultimo_pago,
            (p.total_financiamiento - COALESCE(SUM(cu.total_pagado), 0)) as monto_total_pendiente,
            COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado NOT IN ('PAGADO', 'PARCIAL') THEN 1 END) as cuotas_vencidas_sin_pagar
        FROM 
            prestamos p
            LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE 
            p.estado = 'APROBADO'
            AND p.fecha_aprobacion IS NOT NULL
        GROUP BY 
            p.id, p.cliente_id, p.total_financiamiento, p.fecha_aprobacion
        HAVING 
            COUNT(cu.id) >= 2
    ) features ON p.id = features.prestamo_id
WHERE 
    p.estado = 'APROBADO'
GROUP BY 
    c.id, c.cedula, c.nombre, c.apellido
ORDER BY 
    nivel_riesgo_estimado, total_cuotas_vencidas_sin_pagar DESC;

-- 8.3 Análisis de Riesgo Detallado por Préstamo con Evaluación
-- Combina features de ML Impago con evaluaciones de riesgo existentes
SELECT 
    p.id as prestamo_id,
    c.id as cliente_id,
    c.cedula,
    c.nombre || ' ' || c.apellido as nombre_cliente,
    p.total_financiamiento,
    p.fecha_aprobacion,
    p.estado as estado_prestamo,
    -- Features ML Impago
    CASE 
        WHEN COUNT(cu.id) > 0 THEN 
            (COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END)::numeric / COUNT(cu.id)::numeric * 100)
        ELSE 0 
    END as porcentaje_cuotas_pagadas,
    COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado NOT IN ('PAGADO', 'PARCIAL') THEN 1 END) as cuotas_vencidas_sin_pagar,
    CASE 
        WHEN COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE THEN 1 END) > 0 THEN
            (COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado = 'PAGADO' THEN 1 END)::numeric / 
             COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE THEN 1 END)::numeric * 100)
        ELSE 100 
    END as tasa_cumplimiento,
    COALESCE(AVG(CASE WHEN cu.dias_mora > 0 THEN cu.dias_mora END), 0) as promedio_dias_mora,
    (p.total_financiamiento - COALESCE(SUM(cu.total_pagado), 0)) as monto_total_pendiente,
    -- Evaluación de riesgo (si existe)
    pe.puntuacion_total as puntuacion_evaluacion,
    pe.clasificacion_riesgo as riesgo_evaluacion,
    pe.decision_final as decision_evaluacion,
    -- Riesgo estimado basado en ML Impago
    CASE 
        WHEN COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado NOT IN ('PAGADO', 'PARCIAL') THEN 1 END) > 3 THEN 'ALTO'
        WHEN COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado NOT IN ('PAGADO', 'PARCIAL') THEN 1 END) > 0 THEN 'MEDIO'
        WHEN (COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END)::numeric / NULLIF(COUNT(cu.id), 0)::numeric * 100) >= 80 THEN 'BAJO'
        ELSE 'MODERADO'
    END as nivel_riesgo_ml_impago
FROM 
    prestamos p
    INNER JOIN clientes c ON p.cliente_id = c.id
    LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
    LEFT JOIN prestamos_evaluacion pe ON p.id = pe.prestamo_id
WHERE 
    p.estado = 'APROBADO'
    AND p.fecha_aprobacion IS NOT NULL
GROUP BY 
    p.id, c.id, c.cedula, c.nombre, c.apellido, p.total_financiamiento, 
    p.fecha_aprobacion, p.estado, pe.puntuacion_total, pe.clasificacion_riesgo, pe.decision_final
HAVING 
    COUNT(cu.id) >= 2
ORDER BY 
    cuotas_vencidas_sin_pagar DESC, nivel_riesgo_ml_impago DESC;

-- 8.4 Resumen de Riesgo por Nivel
-- Agrupa clientes por nivel de riesgo estimado
SELECT 
    CASE 
        WHEN SUM(cuotas_vencidas_sin_pagar) > 3 OR AVG(tasa_cumplimiento) < 50 THEN 'ALTO RIESGO'
        WHEN SUM(cuotas_vencidas_sin_pagar) > 0 OR AVG(tasa_cumplimiento) < 70 THEN 'MEDIO RIESGO'
        WHEN AVG(porcentaje_cuotas_pagadas) >= 80 AND AVG(tasa_cumplimiento) >= 90 THEN 'BAJO RIESGO'
        ELSE 'RIESGO MODERADO'
    END as nivel_riesgo,
    COUNT(DISTINCT cliente_id) as total_clientes,
    COUNT(DISTINCT prestamo_id) as total_prestamos,
    AVG(porcentaje_cuotas_pagadas) as porcentaje_cuotas_pagadas_promedio,
    AVG(tasa_cumplimiento) as tasa_cumplimiento_promedio,
    SUM(cuotas_vencidas_sin_pagar) as total_cuotas_vencidas_sin_pagar,
    SUM(monto_total_pendiente) as monto_total_pendiente
FROM (
    SELECT 
        c.id as cliente_id,
        p.id as prestamo_id,
        CASE 
            WHEN COUNT(cu.id) > 0 THEN 
                (COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END)::numeric / COUNT(cu.id)::numeric * 100)
            ELSE 0 
        END as porcentaje_cuotas_pagadas,
        CASE 
            WHEN COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE THEN 1 END) > 0 THEN
                (COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado = 'PAGADO' THEN 1 END)::numeric / 
                 COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE THEN 1 END)::numeric * 100)
            ELSE 100 
        END as tasa_cumplimiento,
        COUNT(CASE WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado NOT IN ('PAGADO', 'PARCIAL') THEN 1 END) as cuotas_vencidas_sin_pagar,
        (p.total_financiamiento - COALESCE(SUM(cu.total_pagado), 0)) as monto_total_pendiente
    FROM 
        prestamos p
        INNER JOIN clientes c ON p.cliente_id = c.id
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
    WHERE 
        p.estado = 'APROBADO'
        AND p.fecha_aprobacion IS NOT NULL
    GROUP BY 
        c.id, p.id, p.total_financiamiento
    HAVING 
        COUNT(cu.id) >= 2
) riesgo_data
GROUP BY 
    nivel_riesgo
ORDER BY 
    CASE nivel_riesgo
        WHEN 'ALTO RIESGO' THEN 1
        WHEN 'MEDIO RIESGO' THEN 2
        WHEN 'RIESGO MODERADO' THEN 3
        WHEN 'BAJO RIESGO' THEN 4
    END;

