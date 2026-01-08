-- ======================================================================
-- SCRIPT PARA DBEAVER: REVISAR CLIENTES INACTIVOS CON PRESTAMOS APROBADOS
-- ======================================================================
-- Este script permite revisar manualmente los casos donde clientes
-- en estado INACTIVO tienen préstamos aprobados, lo cual viola la regla
-- de negocio: "Clientes INACTIVOS (pasivos) no deben tener préstamos aprobados"
-- ======================================================================

-- ======================================================================
-- 1. LISTA DE CLIENTES INACTIVOS CON PRESTAMOS APROBADOS
-- ======================================================================
-- Muestra todos los clientes en estado INACTIVO que tienen préstamos aprobados
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_cliente,
    c.activo,
    c.fecha_registro AS fecha_registro_cliente,
    c.fecha_actualizacion AS fecha_actualizacion_cliente,
    c.telefono,
    c.email,
    COUNT(p.id) AS total_prestamos_aprobados,
    MIN(p.fecha_aprobacion) AS primera_aprobacion,
    MAX(p.fecha_aprobacion) AS ultima_aprobacion
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo, 
         c.fecha_registro, c.fecha_actualizacion, c.telefono, c.email
ORDER BY c.fecha_actualizacion DESC;

-- ======================================================================
-- 2. DETALLE COMPLETO DE PRESTAMOS DE CLIENTES INACTIVOS
-- ======================================================================
-- Muestra información detallada de los préstamos aprobados de clientes INACTIVOS
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres AS nombre_cliente,
    c.estado AS estado_cliente,
    c.activo AS cliente_activo,
    c.fecha_actualizacion AS fecha_inactivacion,
    p.id AS prestamo_id,
    p.estado AS estado_prestamo,
    p.total_financiamiento,
    p.numero_cuotas,
    p.cuota_periodo,
    p.fecha_aprobacion,
    p.fecha_registro AS fecha_registro_prestamo,
    COUNT(cu.id) AS total_cuotas_generadas,
    COALESCE(SUM(cu.total_pagado), 0) AS total_pagado_cuotas,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo, 
         c.fecha_actualizacion, p.id, p.estado, p.total_financiamiento, 
         p.numero_cuotas, p.cuota_periodo, p.fecha_aprobacion, p.fecha_registro
ORDER BY p.fecha_aprobacion DESC;

-- ======================================================================
-- 3. PAGOS REGISTRADOS DE CLIENTES INACTIVOS CON PRESTAMOS
-- ======================================================================
-- Muestra los pagos registrados para estos clientes
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres AS nombre_cliente,
    c.estado AS estado_cliente,
    p.id AS prestamo_id,
    pag.id AS pago_id,
    pag.monto_pagado,
    pag.fecha_pago,
    pag.conciliado,
    pag.activo AS pago_activo,
    pag.fecha_registro AS fecha_registro_pago
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'
ORDER BY c.cedula, pag.fecha_pago DESC;

-- ======================================================================
-- 4. RESUMEN DE PAGOS POR CLIENTE INACTIVO
-- ======================================================================
-- Resumen agregado de pagos por cliente
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres AS nombre_cliente,
    COUNT(DISTINCT p.id) AS total_prestamos_aprobados,
    COUNT(pag.id) AS total_pagos_registrados,
    COALESCE(SUM(pag.monto_pagado), 0) AS total_pagado,
    MIN(pag.fecha_pago) AS primer_pago,
    MAX(pag.fecha_pago) AS ultimo_pago
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres
ORDER BY total_pagado DESC;

-- ======================================================================
-- 5. ANALISIS TEMPORAL: FECHA INACTIVACION VS APROBACION
-- ======================================================================
-- Compara fechas de inactivación vs aprobación para identificar problemas
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres AS nombre_cliente,
    c.fecha_actualizacion AS fecha_inactivacion,
    p.id AS prestamo_id,
    p.fecha_aprobacion,
    CASE 
        WHEN c.fecha_actualizacion < p.fecha_aprobacion THEN 'INACTIVADO ANTES'
        WHEN c.fecha_actualizacion >= p.fecha_aprobacion THEN 'INACTIVADO DESPUES'
        ELSE 'SIN FECHA'
    END AS analisis_temporal,
    CASE 
        WHEN c.fecha_actualizacion < p.fecha_aprobacion 
        THEN EXTRACT(DAY FROM (p.fecha_aprobacion - c.fecha_actualizacion))
        WHEN c.fecha_actualizacion >= p.fecha_aprobacion 
        THEN EXTRACT(DAY FROM (c.fecha_actualizacion - p.fecha_aprobacion))
        ELSE NULL
    END AS dias_diferencia
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'
ORDER BY p.fecha_aprobacion DESC;

-- ======================================================================
-- 6. CUOTAS DETALLADAS DE PRESTAMOS DE CLIENTES INACTIVOS
-- ======================================================================
-- Muestra el detalle de cuotas para revisar el estado de cada una
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres AS nombre_cliente,
    c.estado AS estado_cliente,
    p.id AS prestamo_id,
    cu.numero_cuota,
    cu.fecha_vencimiento,
    cu.monto_cuota,
    cu.total_pagado,
    cu.capital_pendiente,
    cu.interes_pendiente,
    cu.dias_mora,
    cu.monto_mora,
    cu.estado AS estado_cuota
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'
ORDER BY c.cedula, p.id, cu.numero_cuota;

-- ======================================================================
-- 7. ESTADISTICAS GENERALES
-- ======================================================================
-- Resumen estadístico de la situación
-- ======================================================================

SELECT 
    'Total clientes INACTIVOS con prestamos aprobados' AS metrica,
    COUNT(DISTINCT c.id) AS valor
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'

UNION ALL

SELECT 
    'Total prestamos aprobados de clientes INACTIVOS' AS metrica,
    COUNT(p.id) AS valor
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'

UNION ALL

SELECT 
    'Prestamos con cuotas generadas' AS metrica,
    COUNT(DISTINCT p.id) AS valor
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'

UNION ALL

SELECT 
    'Total pagos registrados' AS metrica,
    COUNT(pag.id) AS valor
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'

UNION ALL

SELECT 
    'Total pagado' AS metrica,
    COALESCE(SUM(pag.monto_pagado), 0) AS valor
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO';

-- ======================================================================
-- 8. CASO ESPECIFICO: CLIENTE V20428105 (CASO ENCONTRADO)
-- ======================================================================
-- Query específico para revisar el caso anómalo encontrado
-- ======================================================================

-- Información del cliente
SELECT 
    'CLIENTE' AS tipo_dato,
    c.id,
    c.cedula,
    c.nombres,
    c.estado,
    c.activo,
    c.fecha_registro,
    c.fecha_actualizacion,
    c.telefono,
    c.email,
    NULL AS prestamo_id,
    NULL AS prestamo_estado,
    NULL AS total_financiamiento
FROM clientes c
WHERE c.cedula = 'V20428105'

UNION ALL

-- Información del préstamo
SELECT 
    'PRESTAMO' AS tipo_dato,
    NULL AS id,
    p.cedula,
    NULL AS nombres,
    NULL AS estado,
    NULL AS activo,
    p.fecha_registro,
    p.fecha_aprobacion,
    NULL AS telefono,
    NULL AS email,
    p.id AS prestamo_id,
    p.estado AS prestamo_estado,
    p.total_financiamiento
FROM prestamos p
WHERE p.cedula = 'V20428105'
  AND p.estado = 'APROBADO';

-- ======================================================================
-- NOTAS PARA REVISION MANUAL:
-- ======================================================================
-- 1. Revisar si el cliente debería estar en estado 'FINALIZADO' en lugar de 'INACTIVO'
-- 2. Verificar si el préstamo debería estar aprobado
-- 3. Comprobar si hay pagos registrados que justifiquen el cambio de estado
-- 4. Validar la fecha de inactivación vs fecha de aprobación
-- 5. Considerar si es un error de datos que necesita corrección
-- ======================================================================
