-- ======================================================================
-- VERIFICACION: PRESTAMOS CON TABLA DE AMORTIZACION
-- ======================================================================
-- Objetivo: Verificar que todos los préstamos tienen cuotas generadas
-- ======================================================================

-- ======================================================================
-- 1. RESUMEN GENERAL: PRESTAMOS CON Y SIN CUOTAS
-- ======================================================================

SELECT 
    'Total prestamos' AS metrica,
    COUNT(*) AS valor
FROM prestamos

UNION ALL

SELECT 
    'Prestamos APROBADOS' AS metrica,
    COUNT(*) AS valor
FROM prestamos
WHERE estado = 'APROBADO'

UNION ALL

SELECT 
    'Prestamos CON cuotas generadas' AS metrica,
    COUNT(DISTINCT p.id) AS valor
FROM prestamos p
INNER JOIN cuotas cu ON p.id = cu.prestamo_id

UNION ALL

SELECT 
    'Prestamos SIN cuotas generadas' AS metrica,
    COUNT(DISTINCT p.id) AS valor
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE cu.id IS NULL

UNION ALL

SELECT 
    'Prestamos APROBADOS CON cuotas' AS metrica,
    COUNT(DISTINCT p.id) AS valor
FROM prestamos p
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'

UNION ALL

SELECT 
    'Prestamos APROBADOS SIN cuotas' AS metrica,
    COUNT(DISTINCT p.id) AS valor
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
  AND cu.id IS NULL;

-- ======================================================================
-- 2. PRESTAMOS APROBADOS SIN CUOTAS GENERADAS
-- ======================================================================
-- Estos son los que requieren atención
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.estado AS estado_prestamo,
    p.total_financiamiento,
    p.numero_cuotas,
    p.cuota_periodo,
    p.modalidad_pago,
    p.tasa_interes,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    p.fecha_registro,
    CASE 
        WHEN p.fecha_base_calculo IS NULL THEN 'FALTA fecha_base_calculo'
        ELSE 'TIENE fecha_base_calculo'
    END AS tiene_fecha_base
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
  AND cu.id IS NULL
ORDER BY p.fecha_aprobacion DESC, p.id;

-- ======================================================================
-- 3. ESTADISTICAS POR ESTADO DE PRESTAMO
-- ======================================================================

SELECT 
    p.estado AS estado_prestamo,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT CASE WHEN cu.id IS NOT NULL THEN p.id END) AS prestamos_con_cuotas,
    COUNT(DISTINCT CASE WHEN cu.id IS NULL THEN p.id END) AS prestamos_sin_cuotas,
    ROUND(
        COUNT(DISTINCT CASE WHEN cu.id IS NOT NULL THEN p.id END) * 100.0 / 
        NULLIF(COUNT(DISTINCT p.id), 0), 
        2
    ) AS porcentaje_con_cuotas
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
GROUP BY p.estado
ORDER BY total_prestamos DESC;

-- ======================================================================
-- 4. PRESTAMOS SIN CUOTAS: DETALLE COMPLETO
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    c.estado AS estado_cliente,
    c.activo AS cliente_activo,
    p.estado AS estado_prestamo,
    p.total_financiamiento,
    p.numero_cuotas,
    p.cuota_periodo,
    p.modalidad_pago,
    p.tasa_interes,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    p.fecha_registro,
    CASE 
        WHEN p.fecha_base_calculo IS NULL THEN 'NO'
        ELSE 'SI'
    END AS puede_generar_cuotas,
    COUNT(pag.id) AS total_pagos_registrados,
    COALESCE(SUM(pag.monto_pagado), 0) AS total_pagado
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
WHERE cu.id IS NULL
GROUP BY p.id, p.cedula, c.nombres, c.estado, c.activo, p.estado,
         p.total_financiamiento, p.numero_cuotas, p.cuota_periodo,
         p.modalidad_pago, p.tasa_interes, p.fecha_aprobacion,
         p.fecha_base_calculo, p.fecha_registro
ORDER BY p.estado, p.fecha_aprobacion DESC;

-- ======================================================================
-- 5. PRESTAMOS CON CUOTAS: VERIFICACION DE CONSISTENCIA
-- ======================================================================
-- Verificar que el número de cuotas generadas coincide con numero_cuotas
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(cu.id) AS cuotas_generadas,
    CASE 
        WHEN COUNT(cu.id) = p.numero_cuotas THEN 'OK'
        WHEN COUNT(cu.id) < p.numero_cuotas THEN 'FALTAN CUOTAS'
        WHEN COUNT(cu.id) > p.numero_cuotas THEN 'CUOTAS DE MAS'
        ELSE 'SIN CUOTAS'
    END AS estado_cuotas,
    p.total_financiamiento,
    COALESCE(SUM(cu.monto_cuota), 0) AS total_cuotas_calculado,
    ABS(p.total_financiamiento - COALESCE(SUM(cu.monto_cuota), 0)) AS diferencia
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, p.total_financiamiento
HAVING COUNT(cu.id) != p.numero_cuotas 
    OR COUNT(cu.id) = 0
    OR ABS(p.total_financiamiento - COALESCE(SUM(cu.monto_cuota), 0)) > 0.01
ORDER BY diferencia DESC, p.id
LIMIT 50;

-- ======================================================================
-- 6. RESUMEN POR MODALIDAD DE PAGO
-- ======================================================================

SELECT 
    p.modalidad_pago,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT CASE WHEN cu.id IS NOT NULL THEN p.id END) AS prestamos_con_cuotas,
    COUNT(DISTINCT CASE WHEN cu.id IS NULL THEN p.id END) AS prestamos_sin_cuotas
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.modalidad_pago
ORDER BY total_prestamos DESC;

-- ======================================================================
-- 7. PRESTAMOS SIN fecha_base_calculo (NO PUEDEN GENERAR CUOTAS)
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.estado AS estado_prestamo,
    p.total_financiamiento,
    p.numero_cuotas,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    p.fecha_registro
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
WHERE p.estado = 'APROBADO'
  AND p.fecha_base_calculo IS NULL
ORDER BY p.fecha_aprobacion DESC;

-- ======================================================================
-- 8. VERIFICACION FINAL: ¿TODOS LOS PRESTAMOS APROBADOS TIENEN CUOTAS?
-- ======================================================================

SELECT 
    CASE 
        WHEN COUNT(CASE WHEN p.estado = 'APROBADO' AND cu.id IS NULL THEN 1 END) = 0 
        THEN 'SI: Todos los prestamos APROBADOS tienen cuotas generadas'
        ELSE CONCAT(
            'NO: Hay ', 
            COUNT(CASE WHEN p.estado = 'APROBADO' AND cu.id IS NULL THEN 1 END), 
            ' prestamos APROBADOS sin cuotas'
        )
    END AS verificacion,
    COUNT(CASE WHEN p.estado = 'APROBADO' THEN 1 END) AS total_prestamos_aprobados,
    COUNT(CASE WHEN p.estado = 'APROBADO' AND cu.id IS NOT NULL THEN 1 END) AS prestamos_aprobados_con_cuotas,
    COUNT(CASE WHEN p.estado = 'APROBADO' AND cu.id IS NULL THEN 1 END) AS prestamos_aprobados_sin_cuotas
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id;

-- ======================================================================
-- NOTAS:
-- ======================================================================
-- Esta verificación es crítica después de una migración de BD
-- Si hay préstamos aprobados sin cuotas, deben generarse usando:
-- 1. Script: scripts/python/Generar_Cuotas_Masivas.py
-- 2. O endpoint API: POST /api/v1/prestamos/{id}/generar-amortizacion
-- ======================================================================
