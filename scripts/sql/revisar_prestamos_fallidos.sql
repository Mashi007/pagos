-- ============================================================================
-- SCRIPT PARA REVISAR PRÉSTAMOS FALLIDOS EN LA GENERACIÓN DE CUOTAS
-- ============================================================================
-- Préstamos que fallaron: 4468, 4475, 4476, 4522, y posiblemente uno más
-- ============================================================================

-- 1. INFORMACIÓN GENERAL DE LOS PRÉSTAMOS FALLIDOS
-- ============================================================================
SELECT 
    'INFORMACIÓN GENERAL' as tipo,
    p.id as prestamo_id,
    p.cedula,
    p.estado,
    p.fecha_base_calculo,
    p.numero_cuotas,
    p.total_financiamiento,
    p.cuota_periodo,
    p.tasa_interes,
    p.modalidad_pago,
    CASE 
        WHEN p.fecha_base_calculo IS NULL THEN '❌ FALTA fecha_base_calculo'
        WHEN p.numero_cuotas IS NULL OR p.numero_cuotas <= 0 THEN '❌ FALTA numero_cuotas'
        WHEN p.total_financiamiento IS NULL OR p.total_financiamiento <= 0 THEN '❌ FALTA total_financiamiento'
        WHEN p.cuota_periodo IS NULL OR p.cuota_periodo <= 0 THEN '❌ FALTA cuota_periodo'
        WHEN p.modalidad_pago NOT IN ('MENSUAL', 'QUINCENAL', 'SEMANAL') THEN '❌ modalidad_pago inválida'
        ELSE '✓ Datos completos'
    END as validacion_datos,
    (SELECT COUNT(*) FROM cuotas WHERE prestamo_id = p.id) as cuotas_existentes
FROM prestamos p
WHERE p.id IN (4468, 4475, 4476, 4522)
ORDER BY p.id;

-- 2. VERIFICAR SI TIENEN CUOTAS EXISTENTES
-- ============================================================================
SELECT 
    'CUOTAS EXISTENTES' as tipo,
    c.prestamo_id,
    COUNT(*) as total_cuotas,
    MIN(c.numero_cuota) as primera_cuota,
    MAX(c.numero_cuota) as ultima_cuota,
    SUM(c.total_pagado) as total_pagado_acumulado
FROM cuotas c
WHERE c.prestamo_id IN (4468, 4475, 4476, 4522)
GROUP BY c.prestamo_id
ORDER BY c.prestamo_id;

-- 3. DETALLES DE CUOTAS EXISTENTES (si las hay)
-- ============================================================================
SELECT 
    'DETALLE CUOTAS' as tipo,
    c.id,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.monto_capital,
    c.monto_interes,
    c.total_pagado,
    c.estado
FROM cuotas c
WHERE c.prestamo_id IN (4468, 4475, 4476, 4522)
ORDER BY c.prestamo_id, c.numero_cuota;

-- 4. VERIFICAR DATOS ESPECÍFICOS QUE PODRÍAN CAUSAR ERRORES
-- ============================================================================
SELECT 
    'VALIDACIÓN DETALLADA' as tipo,
    p.id as prestamo_id,
    p.cedula,
    -- Verificar tipos de datos
    pg_typeof(p.fecha_base_calculo) as tipo_fecha_base,
    pg_typeof(p.numero_cuotas) as tipo_numero_cuotas,
    pg_typeof(p.total_financiamiento) as tipo_total_financiamiento,
    pg_typeof(p.cuota_periodo) as tipo_cuota_periodo,
    pg_typeof(p.tasa_interes) as tipo_tasa_interes,
    -- Verificar valores
    p.fecha_base_calculo,
    p.numero_cuotas,
    p.total_financiamiento,
    p.cuota_periodo,
    COALESCE(p.tasa_interes, 0) as tasa_interes,
    p.modalidad_pago,
    -- Verificar si los valores son válidos para cálculos
    CASE 
        WHEN p.total_financiamiento <= 0 THEN '❌ total_financiamiento <= 0'
        WHEN p.numero_cuotas <= 0 THEN '❌ numero_cuotas <= 0'
        WHEN p.cuota_periodo <= 0 THEN '❌ cuota_periodo <= 0'
        WHEN p.fecha_base_calculo IS NULL THEN '❌ fecha_base_calculo NULL'
        WHEN p.modalidad_pago NOT IN ('MENSUAL', 'QUINCENAL', 'SEMANAL') THEN '❌ modalidad_pago inválida'
        ELSE '✓ Valores válidos'
    END as validacion_valores
FROM prestamos p
WHERE p.id IN (4468, 4475, 4476, 4522)
ORDER BY p.id;

-- 5. BUSCAR OTROS PRÉSTAMOS APROBADOS SIN CUOTAS (por si hay más fallidos)
-- ============================================================================
SELECT 
    'OTROS SIN CUOTAS' as tipo,
    COUNT(*) as total_prestamos_sin_cuotas,
    STRING_AGG(p.id::text, ', ' ORDER BY p.id) as ids_prestamos
FROM prestamos p
WHERE p.estado = 'APROBADO'
  AND p.fecha_base_calculo IS NOT NULL
  AND p.numero_cuotas IS NOT NULL
  AND p.numero_cuotas > 0
  AND p.total_financiamiento IS NOT NULL
  AND p.total_financiamiento > 0
  AND p.cuota_periodo IS NOT NULL
  AND p.cuota_periodo > 0
  AND p.modalidad_pago IN ('MENSUAL', 'QUINCENAL', 'SEMANAL')
  AND NOT EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = p.id)
  AND p.id NOT IN (4468, 4475, 4476, 4522);

-- 6. COMPARAR CON PRÉSTAMOS EXITOSOS SIMILARES
-- ============================================================================
SELECT 
    'COMPARACIÓN CON EXITOSOS' as tipo,
    p.id as prestamo_id,
    p.cedula,
    p.modalidad_pago,
    p.numero_cuotas,
    p.total_financiamiento,
    p.cuota_periodo,
    p.tasa_interes,
    (SELECT COUNT(*) FROM cuotas WHERE prestamo_id = p.id) as cuotas_generadas,
    CASE 
        WHEN EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = p.id) THEN '✓ Tiene cuotas'
        ELSE '❌ Sin cuotas'
    END as estado_cuotas
FROM prestamos p
WHERE p.estado = 'APROBADO'
  AND p.modalidad_pago IN (SELECT DISTINCT modalidad_pago FROM prestamos WHERE id IN (4468, 4475, 4476, 4522))
  AND p.id NOT IN (4468, 4475, 4476, 4522)
  AND EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = p.id)
ORDER BY p.modalidad_pago, p.id
LIMIT 10;
