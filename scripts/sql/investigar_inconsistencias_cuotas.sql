-- ======================================================================
-- INVESTIGACION: INCONSISTENCIAS EN CUOTAS DE PRESTAMOS
-- ======================================================================
-- Objetivo: Investigar préstamos con cuotas de más o cuotas faltantes
-- ======================================================================

-- ======================================================================
-- 1. PRESTAMOS CON CUOTAS DE MAS (MÁS CUOTAS DE LAS PLANIFICADAS)
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(cu.id) AS cuotas_generadas,
    COUNT(cu.id) - p.numero_cuotas AS cuotas_extra,
    ROUND((COUNT(cu.id)::numeric / p.numero_cuotas::numeric), 2) AS multiplicador,
    p.total_financiamiento,
    p.cuota_periodo,
    p.modalidad_pago,
    p.tasa_interes,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    MIN(cu.fecha_vencimiento) AS primera_cuota,
    MAX(cu.fecha_vencimiento) AS ultima_cuota,
    COUNT(DISTINCT DATE_TRUNC('month', cu.fecha_vencimiento)) AS meses_distintos,
    COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN cu.estado != 'PAGADO' THEN 1 END) AS cuotas_pendientes
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, p.total_financiamiento,
         p.cuota_periodo, p.modalidad_pago, p.tasa_interes, p.fecha_aprobacion,
         p.fecha_base_calculo
HAVING COUNT(cu.id) > p.numero_cuotas
ORDER BY (COUNT(cu.id) - p.numero_cuotas) DESC, p.id;

-- ======================================================================
-- 2. DETALLE DE CUOTAS PARA PRESTAMOS CON CUOTAS DE MAS
-- ======================================================================
-- Ver las cuotas generadas para entender el patrón
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    cu.numero_cuota,
    cu.fecha_vencimiento,
    cu.monto_cuota,
    cu.estado AS estado_cuota,
    cu.capital_pendiente,
    cu.interes_pendiente,
    cu.total_pagado,
    cu.fecha_pago,
    ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY cu.numero_cuota) AS orden_secuencial
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
  AND p.id IN (
      SELECT p2.id
      FROM prestamos p2
      INNER JOIN cuotas cu2 ON p2.id = cu2.prestamo_id
      WHERE p2.estado = 'APROBADO'
      GROUP BY p2.id, p2.numero_cuotas
      HAVING COUNT(cu2.id) > p2.numero_cuotas
  )
ORDER BY p.id, cu.numero_cuota
LIMIT 100;

-- ======================================================================
-- 3. PRESTAMOS CON CUOTAS FALTANTES (MENOS CUOTAS DE LAS PLANIFICADAS)
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(cu.id) AS cuotas_generadas,
    p.numero_cuotas - COUNT(cu.id) AS cuotas_faltantes,
    ROUND((COUNT(cu.id)::numeric / p.numero_cuotas::numeric) * 100, 2) AS porcentaje_generado,
    p.total_financiamiento,
    p.cuota_periodo,
    p.modalidad_pago,
    p.tasa_interes,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    MIN(cu.fecha_vencimiento) AS primera_cuota,
    MAX(cu.fecha_vencimiento) AS ultima_cuota,
    COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN cu.estado != 'PAGADO' THEN 1 END) AS cuotas_pendientes
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, p.total_financiamiento,
         p.cuota_periodo, p.modalidad_pago, p.tasa_interes, p.fecha_aprobacion,
         p.fecha_base_calculo
HAVING COUNT(cu.id) < p.numero_cuotas
ORDER BY (p.numero_cuotas - COUNT(cu.id)) DESC, p.id;

-- ======================================================================
-- 4. RANGO DE NUMEROS DE CUOTA GENERADOS (PARA DETECTAR PATRONES)
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(cu.id) AS cuotas_generadas,
    MIN(cu.numero_cuota) AS primera_cuota_numero,
    MAX(cu.numero_cuota) AS ultima_cuota_numero,
    STRING_AGG(DISTINCT cu.numero_cuota::text, ', ' ORDER BY cu.numero_cuota::text) AS numeros_cuotas,
    CASE 
        WHEN COUNT(cu.id) > p.numero_cuotas THEN 'CUOTAS DE MAS'
        WHEN COUNT(cu.id) < p.numero_cuotas THEN 'CUOTAS FALTANTES'
        ELSE 'OK'
    END AS tipo_inconsistencia
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas
HAVING COUNT(cu.id) != p.numero_cuotas
ORDER BY ABS(COUNT(cu.id) - p.numero_cuotas) DESC, p.id
LIMIT 30;

-- ======================================================================
-- 5. VERIFICAR SI HAY CUOTAS DUPLICADAS (MISMO numero_cuota)
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    cu.numero_cuota,
    COUNT(*) AS veces_duplicada,
    STRING_AGG(cu.id::text, ', ' ORDER BY cu.id) AS ids_cuotas,
    STRING_AGG(cu.fecha_vencimiento::text, ', ' ORDER BY cu.fecha_vencimiento) AS fechas_vencimiento
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, cu.numero_cuota
HAVING COUNT(*) > 1
ORDER BY p.id, cu.numero_cuota;

-- ======================================================================
-- 6. ANALISIS TEMPORAL: FECHAS DE GENERACION DE CUOTAS
-- ======================================================================
-- Ver si las cuotas fueron generadas en diferentes momentos
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(cu.id) AS cuotas_generadas,
    MIN(cu.fecha_registro) AS primera_cuota_registrada,
    MAX(cu.fecha_registro) AS ultima_cuota_registrada,
    COUNT(DISTINCT DATE(cu.fecha_registro)) AS dias_distintos_generacion,
    CASE 
        WHEN COUNT(DISTINCT DATE(cu.fecha_registro)) > 1 THEN 'GENERADAS EN MULTIPLES DIAS'
        ELSE 'GENERADAS EN UN SOLO DIA'
    END AS patron_generacion
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
  AND p.id IN (
      SELECT p2.id
      FROM prestamos p2
      INNER JOIN cuotas cu2 ON p2.id = cu2.prestamo_id
      WHERE p2.estado = 'APROBADO'
      GROUP BY p2.id, p2.numero_cuotas
      HAVING COUNT(cu2.id) != p2.numero_cuotas
  )
GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas
ORDER BY COUNT(DISTINCT DATE(cu.fecha_registro)) DESC, p.id;

-- ======================================================================
-- 7. CASOS ESPECIFICOS: PRESTAMOS CON MAS DEL DOBLE DE CUOTAS
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(cu.id) AS cuotas_generadas,
    ROUND((COUNT(cu.id)::numeric / p.numero_cuotas::numeric), 2) AS multiplicador,
    p.total_financiamiento,
    p.cuota_periodo,
    p.modalidad_pago,
    p.fecha_aprobacion,
    COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN cu.estado != 'PAGADO' THEN 1 END) AS cuotas_pendientes,
    COALESCE(SUM(cu.total_pagado), 0) AS total_pagado_cuotas
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, p.total_financiamiento,
         p.cuota_periodo, p.modalidad_pago, p.fecha_aprobacion
HAVING COUNT(cu.id) >= (p.numero_cuotas * 2)
ORDER BY (COUNT(cu.id) / p.numero_cuotas) DESC, p.id;

-- ======================================================================
-- 8. RESUMEN DE INCONSISTENCIAS POR TIPO
-- ======================================================================

SELECT 
    CASE 
        WHEN COUNT(cu.id) > p.numero_cuotas THEN 'CUOTAS DE MAS'
        WHEN COUNT(cu.id) < p.numero_cuotas THEN 'CUOTAS FALTANTES'
        ELSE 'OK'
    END AS tipo_inconsistencia,
    COUNT(DISTINCT p.id) AS total_prestamos,
    SUM(COUNT(cu.id) - p.numero_cuotas) AS diferencia_total_cuotas,
    AVG(COUNT(cu.id) - p.numero_cuotas) AS diferencia_promedio,
    MIN(COUNT(cu.id) - p.numero_cuotas) AS diferencia_minima,
    MAX(COUNT(cu.id) - p.numero_cuotas) AS diferencia_maxima
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.numero_cuotas
HAVING COUNT(cu.id) != p.numero_cuotas
GROUP BY tipo_inconsistencia
ORDER BY total_prestamos DESC;

-- ======================================================================
-- NOTAS:
-- ======================================================================
-- Esta investigación ayuda a entender:
-- 1. Si hay cuotas duplicadas (mismo numero_cuota)
-- 2. Si las cuotas fueron generadas en múltiples ocasiones
-- 3. Patrones de regeneración (multiplicadores: 2x, 3x, 4x)
-- 4. Si faltan cuotas específicas o todas las últimas
-- ======================================================================
