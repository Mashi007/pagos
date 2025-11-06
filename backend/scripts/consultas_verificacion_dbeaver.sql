-- ============================================
-- CONSULTAS PARA VERIFICAR EN DBEAVER
-- Sistema de Préstamos con Evaluación de Riesgo
-- ============================================

-- ============================================
-- 1. VERIFICAR TABLAS EXISTENTES
-- ============================================

-- Tabla 1: PRESTAMOS (Formulario "Nuevo Préstamo")
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    p.total_financiamiento,
    p.fecha_requerimiento,
    p.modalidad_pago,
    p.numero_cuotas,
    p.cuota_periodo,
    p.tasa_interes,
    p.producto,
    p.producto_financiero,
    p.estado,
    p.fecha_solicitud,
    p.usuario_aprobador,
    p.fecha_aprobacion,
    p.created_at
FROM prestamos p
ORDER BY p.id DESC
LIMIT 10;

-- Tabla 2: PRESTAMOS_EVALUACION (Formulario "Evaluación de Riesgo")
SELECT 
    e.id,
    e.prestamo_id,
    -- Criterio 1: Capacidad de Pago (33 puntos)
    e.ratio_endeudamiento_puntos,
    e.ratio_endeudamiento_calculo,
    e.ratio_cobertura_puntos,
    e.ratio_cobertura_calculo,
    -- Criterio 2: Estabilidad Laboral (23 puntos)
    e.antiguedad_trabajo_puntos,
    e.meses_trabajo,
    e.tipo_empleo_puntos,
    e.tipo_empleo_descripcion,
    e.sector_economico_puntos,
    e.sector_economico_descripcion,
    -- Criterio 3: Referencias (5 puntos)
    e.referencias_puntos,
    e.referencias_descripcion,
    e.num_referencias_verificadas,
    -- Criterio 4: Arraigo Geográfico (12 puntos)
    e.arraigo_vivienda_puntos,
    e.arraigo_familiar_puntos,
    e.arraigo_laboral_puntos,
    -- Criterio 5: Perfil Sociodemográfico (17 puntos)
    e.vivienda_puntos,
    e.vivienda_descripcion,
    e.estado_civil_puntos,
    e.estado_civil_descripcion,
    e.hijos_puntos,
    e.hijos_descripcion,
    -- Criterio 6: Edad (5 puntos)
    e.edad_puntos,
    e.edad_cliente,
    -- Criterio 7: Enganche (5 puntos)
    e.enganche_garantias_puntos,
    e.enganche_garantias_calculo,
    -- Totales
    e.puntuacion_total,
    e.clasificacion_riesgo,
    e.decision_final,
    e.tasa_interes_aplicada,
    e.plazo_maximo,
    e.enganche_minimo,
    e.requisitos_adicionales,
    -- Compatibilidad (campos antiguos)
    e.historial_crediticio_puntos,
    e.historial_crediticio_descripcion,
    e.anos_empleo
FROM prestamos_evaluacion e
ORDER BY e.id DESC
LIMIT 10;

-- ============================================
-- 2. JOINT PARA VER RELACIÓN ENTRE TABLAS
-- ============================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.estado AS estado_prestamo,
    p.total_financiamiento,
    p.cuota_periodo,
    e.id AS evaluacion_id,
    e.puntuacion_total,
    e.clasificacion_riesgo,
    e.decision_final,
    e.tasa_interes_aplicada,
    e.plazo_maximo,
    e.enganche_minimo,
    e.requisitos_adicionales,
    -- Desglose de criterios
    e.ratio_endeudamiento_puntos + e.ratio_cobertura_puntos AS criterio_1_total,
    e.antiguedad_trabajo_puntos + e.tipo_empleo_puntos + e.sector_economico_puntos AS criterio_2_total,
    e.referencias_puntos AS criterio_3_total,
    e.arraigo_vivienda_puntos + e.arraigo_familiar_puntos + e.arraigo_laboral_puntos AS criterio_4_total,
    e.vivienda_puntos + e.estado_civil_puntos + e.hijos_puntos AS criterio_5_total,
    e.edad_puntos AS criterio_6_total,
    e.enganche_garantias_puntos AS criterio_7_total
FROM prestamos p
LEFT JOIN prestamos_evaluacion e ON p.id = e.prestamo_id
ORDER BY p.id DESC
LIMIT 10;

-- ============================================
-- 3. CONTAR REGISTROS EN CADA TABLA
-- ============================================

SELECT 
    'prestamos' AS tabla,
    COUNT(*) AS total_registros
FROM prestamos
UNION ALL
SELECT 
    'prestamos_evaluacion' AS tabla,
    COUNT(*) AS total_registros
FROM prestamos_evaluacion;

-- ============================================
-- 4. VERIFICAR PRESTAMOS CON/SIN EVALUACIÓN
-- ============================================

SELECT 
    'Con evaluación' AS tipo,
    COUNT(*) AS cantidad
FROM prestamos p
INNER JOIN prestamos_evaluacion e ON p.id = e.prestamo_id
UNION ALL
SELECT 
    'Sin evaluación' AS tipo,
    COUNT(*) AS cantidad
FROM prestamos p
LEFT JOIN prestamos_evaluacion e ON p.id = e.prestamo_id
WHERE e.id IS NULL;

-- ============================================
-- 5. RESUMEN DE PUNTUACIONES POR CLASIFICACIÓN
-- ============================================

SELECT 
    e.clasificacion_riesgo,
    e.decision_final,
    COUNT(*) AS cantidad,
    AVG(e.puntuacion_total) AS promedio_puntos,
    MIN(e.puntuacion_total) AS minimo_puntos,
    MAX(e.puntuacion_total) AS maximo_puntos
FROM prestamos_evaluacion e
GROUP BY e.clasificacion_riesgo, e.decision_final
ORDER BY 
    CASE e.clasificacion_riesgo
        WHEN 'A' THEN 1
        WHEN 'B' THEN 2
        WHEN 'C' THEN 3
        WHEN 'D' THEN 4
        WHEN 'E' THEN 5
    END;

-- ============================================
-- 6. VER DETALLE DE CRITERIOS DE UNA EVALUACIÓN
-- ============================================

-- Reemplazar el prestamo_id con un ID real
SELECT 
    'Criterio 1: Capacidad de Pago (33 pts)' AS criterio,
    e.ratio_endeudamiento_puntos + e.ratio_cobertura_puntos AS puntos_obtenidos,
    33 AS puntos_maximos
FROM prestamos_evaluacion e
WHERE e.prestamo_id = 1  -- CAMBIAR ID
UNION ALL
SELECT 
    'Criterio 2: Estabilidad Laboral (23 pts)' AS criterio,
    e.antiguedad_trabajo_puntos + e.tipo_empleo_puntos + e.sector_economico_puntos AS puntos_obtenidos,
    23 AS puntos_maximos
FROM prestamos_evaluacion e
WHERE e.prestamo_id = 1  -- CAMBIAR ID
UNION ALL
SELECT 
    'Criterio 3: Referencias (5 pts)' AS criterio,
    e.referencias_puntos AS puntos_obtenidos,
    5 AS puntos_maximos
FROM prestamos_evaluacion e
WHERE e.prestamo_id = 1  -- CAMBIAR ID
UNION ALL
SELECT 
    'Criterio 4: Arraigo Geográfico (12 pts)' AS criterio,
    e.arraigo_vivienda_puntos + e.arraigo_familiar_puntos + e.arraigo_laboral_puntos AS puntos_obtenidos,
    12 AS puntos_maximos
FROM prestamos_evaluacion e
WHERE e.prestamo_id = 1  -- CAMBIAR ID
UNION ALL
SELECT 
    'Criterio 5: Perfil Sociodemográfico (17 pts)' AS criterio,
    e.vivienda_puntos + e.estado_civil_puntos + e.hijos_puntos AS puntos_obtenidos,
    17 AS puntos_maximos
FROM prestamos_evaluacion e
WHERE e.prestamo_id = 1  -- CAMBIAR ID
UNION ALL
SELECT 
    'Criterio 6: Edad (5 pts)' AS criterio,
    e.edad_puntos AS puntos_obtenidos,
    5 AS puntos_maximos
FROM prestamos_evaluacion e
WHERE e.prestamo_id = 1  -- CAMBIAR ID
UNION ALL
SELECT 
    'Criterio 7: Enganche (5 pts)' AS criterio,
    e.enganche_garantias_puntos AS puntos_obtenidos,
    5 AS puntos_maximos
FROM prestamos_evaluacion e
WHERE e.prestamo_id = 1;  -- CAMBIAR ID

-- ============================================
-- 7. VER ESTRUCTURA DE LAS TABLAS
-- ============================================

-- PostgreSQL
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'prestamos'
ORDER BY ordinal_position;

SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'prestamos_evaluacion'
ORDER BY ordinal_position;

-- ============================================
-- 8. ESTADÍSTICAS POR DECISIÓN FINAL
-- ============================================

SELECT 
    e.decision_final,
    COUNT(*) AS total,
    AVG(e.puntuacion_total) AS promedio_puntos,
    STRING_AGG(DISTINCT e.clasificacion_riesgo, ', ') AS clasificaciones,
    STRING_AGG(DISTINCT p.estado, ', ') AS estados_prestamo
FROM prestamos_evaluacion e
LEFT JOIN prestamos p ON e.prestamo_id = p.id
GROUP BY e.decision_final
ORDER BY total DESC;

