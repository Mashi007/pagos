-- ============================================
-- VERIFICACIÓN: Comparar Datos del Excel con BD
-- ============================================
-- 
-- Este script verifica si los datos del Excel existen en la BD
-- y compara los valores para identificar inconsistencias.
--
-- INSTRUCCIONES:
-- 1. Reemplaza los valores en la sección "DATOS DEL EXCEL" con los datos reales
-- 2. Ejecuta el script para verificar cada registro
--
-- ============================================

-- ============================================
-- DATOS DEL EXCEL (EJEMPLO - Reemplazar con datos reales)
-- ============================================

-- Ejemplo del Excel mostrado:
-- CLIENTE: YOLMER SAUL SUAREZ
-- CEDULA: V23107415
-- TOTAL FINANCIAMIENTO: 864
-- ABONOS: 630
-- SALDO DEUDOR: 234
-- CUOTAS: 18
-- MODALIDAD: QUINCENAL
-- MONTO CANCELADO CUOTA: 48

-- ============================================
-- VERIFICACIÓN 1: Cliente existe
-- ============================================
SELECT 
    'VERIFICACION CLIENTE' AS tipo,
    'V23107415' AS cedula_excel,
    c.id AS cliente_id,
    c.cedula AS cedula_bd,
    c.nombres AS nombres_bd,
    CASE 
        WHEN c.id IS NULL THEN 'CLIENTE NO EXISTE'
        ELSE 'CLIENTE EXISTE'
    END AS estado
FROM clientes c
WHERE c.cedula = 'V23107415';

-- ============================================
-- VERIFICACIÓN 2: Préstamo existe y datos coinciden
-- ============================================
SELECT 
    'VERIFICACION PRESTAMO' AS tipo,
    'V23107415' AS cedula_excel,
    864.00 AS total_financiamiento_excel,
    18 AS cuotas_excel,
    'QUINCENAL' AS modalidad_excel,
    48.00 AS monto_cuota_excel,
    p.id AS prestamo_id,
    p.cedula AS cedula_bd,
    p.total_financiamiento AS total_financiamiento_bd,
    p.numero_cuotas AS cuotas_bd,
    p.modalidad_pago AS modalidad_bd,
    p.cuota_periodo AS cuota_periodo_bd,
    CASE 
        WHEN p.id IS NULL THEN 'PRESTAMO NO EXISTE'
        WHEN ABS(p.total_financiamiento - 864.00) > 0.01 THEN 'TOTAL FINANCIAMIENTO DIFERENTE'
        WHEN p.numero_cuotas != 18 THEN 'NUMERO CUOTAS DIFERENTE'
        WHEN UPPER(p.modalidad_pago) != 'QUINCENAL' THEN 'MODALIDAD DIFERENTE'
        ELSE 'DATOS COINCIDEN'
    END AS estado
FROM prestamos p
WHERE p.cedula = 'V23107415'
  AND ABS(p.total_financiamiento - 864.00) < 100  -- Tolerancia para encontrar préstamo similar
ORDER BY ABS(p.total_financiamiento - 864.00)
LIMIT 5;

-- ============================================
-- VERIFICACIÓN 3: Cuotas y pagos
-- ============================================
SELECT 
    'VERIFICACION CUOTAS Y PAGOS' AS tipo,
    'V23107415' AS cedula_excel,
    630.00 AS abonos_excel,
    234.00 AS saldo_deudor_excel,
    p.id AS prestamo_id,
    COUNT(c.id) AS cuotas_generadas,
    COALESCE(SUM(c.monto_cuota), 0) AS suma_cuotas,
    COALESCE(SUM(c.total_pagado), 0) AS total_pagado_bd,
    COALESCE(SUM(c.monto_cuota - c.total_pagado), 0) AS saldo_pendiente_bd,
    COALESCE(SUM(pag.monto_pagado), 0) AS total_pagos_bd,
    CASE 
        WHEN ABS(COALESCE(SUM(c.total_pagado), 0) - 630.00) > 0.01 THEN 'ABONOS DIFERENTES'
        WHEN ABS(COALESCE(SUM(c.monto_cuota - c.total_pagado), 0) - 234.00) > 5.00 THEN 'SALDO DEUDOR DIFERENTE'
        ELSE 'DATOS COINCIDEN'
    END AS estado
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
LEFT JOIN pagos pag ON p.id = pag.prestamo_id
WHERE p.cedula = 'V23107415'
  AND ABS(p.total_financiamiento - 864.00) < 100
GROUP BY p.id
ORDER BY ABS(p.total_financiamiento - 864.00)
LIMIT 5;

-- ============================================
-- VERIFICACIÓN 4: Resumen completo
-- ============================================
SELECT 
    'RESUMEN COMPLETO' AS tipo,
    'V23107415' AS cedula_excel,
    'YOLMER SAUL SUAREZ' AS cliente_excel,
    c.id AS cliente_id_bd,
    CASE WHEN c.id IS NULL THEN 'NO EXISTE' ELSE 'EXISTE' END AS cliente_estado,
    p.id AS prestamo_id_bd,
    CASE WHEN p.id IS NULL THEN 'NO EXISTE' ELSE 'EXISTE' END AS prestamo_estado,
    p.total_financiamiento AS total_financiamiento_bd,
    CASE WHEN ABS(COALESCE(p.total_financiamiento, 0) - 864.00) > 0.01 THEN 'DIFERENTE' ELSE 'COINCIDE' END AS total_financiamiento_estado,
    p.numero_cuotas AS cuotas_bd,
    CASE WHEN COALESCE(p.numero_cuotas, 0) != 18 THEN 'DIFERENTE' ELSE 'COINCIDE' END AS cuotas_estado,
    p.modalidad_pago AS modalidad_bd,
    CASE WHEN UPPER(COALESCE(p.modalidad_pago, '')) != 'QUINCENAL' THEN 'DIFERENTE' ELSE 'COINCIDE' END AS modalidad_estado,
    COALESCE(SUM(c.total_pagado), 0) AS abonos_bd,
    CASE WHEN ABS(COALESCE(SUM(c.total_pagado), 0) - 630.00) > 0.01 THEN 'DIFERENTE' ELSE 'COINCIDE' END AS abonos_estado,
    COALESCE(SUM(c.monto_cuota - c.total_pagado), 0) AS saldo_deudor_bd,
    CASE WHEN ABS(COALESCE(SUM(c.monto_cuota - c.total_pagado), 0) - 234.00) > 5.00 THEN 'DIFERENTE' ELSE 'COINCIDE' END AS saldo_estado
FROM clientes c
FULL OUTER JOIN prestamos p ON c.cedula = p.cedula AND ABS(p.total_financiamiento - 864.00) < 100
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.cedula = 'V23107415' OR p.cedula = 'V23107415'
GROUP BY c.id, p.id, p.total_financiamiento, p.numero_cuotas, p.modalidad_pago
ORDER BY ABS(COALESCE(p.total_financiamiento, 0) - 864.00)
LIMIT 5;

-- ============================================
-- PLANTILLA PARA MÚLTIPLES REGISTROS
-- ============================================
-- Si tienes múltiples registros del Excel, puedes crear una tabla temporal
-- y comparar todos a la vez:

-- Crear tabla temporal con datos del Excel
CREATE TEMP TABLE IF NOT EXISTS datos_excel_temp (
    cliente VARCHAR(100),
    cedula VARCHAR(20),
    fecha_no DATE,
    monto_cancelado_cuota NUMERIC(12,2),
    total_financiamiento NUMERIC(12,2),
    abonos NUMERIC(12,2),
    saldo_deudor NUMERIC(12,2),
    fecha_entrega DATE,
    cuotas INTEGER,
    modalidad_financiamiento VARCHAR(20)
);

-- Insertar datos del Excel (ejemplo - reemplazar con datos reales)
-- INSERT INTO datos_excel_temp VALUES
-- ('YOLMER SAUL SUAREZ', 'V23107415', '2024-10-14', 48.00, 864.00, 630.00, 234.00, '2024-10-18', 18, 'QUINCENAL'),
-- ('OTRO CLIENTE', 'V12345678', '2024-10-15', 96.00, 1152.00, 500.00, 652.00, '2024-10-20', 12, 'MENSUAL');

-- Comparar todos los registros
-- SELECT 
--     e.cedula AS cedula_excel,
--     e.cliente AS cliente_excel,
--     e.total_financiamiento AS total_financiamiento_excel,
--     e.abonos AS abonos_excel,
--     e.saldo_deudor AS saldo_deudor_excel,
--     c.id AS cliente_id_bd,
--     p.id AS prestamo_id_bd,
--     p.total_financiamiento AS total_financiamiento_bd,
--     COALESCE(SUM(cu.total_pagado), 0) AS abonos_bd,
--     COALESCE(SUM(cu.monto_cuota - cu.total_pagado), 0) AS saldo_deudor_bd,
--     CASE 
--         WHEN c.id IS NULL THEN 'CLIENTE NO EXISTE'
--         WHEN p.id IS NULL THEN 'PRESTAMO NO EXISTE'
--         WHEN ABS(p.total_financiamiento - e.total_financiamiento) > 0.01 THEN 'TOTAL DIFERENTE'
--         WHEN ABS(COALESCE(SUM(cu.total_pagado), 0) - e.abonos) > 0.01 THEN 'ABONOS DIFERENTES'
--         WHEN ABS(COALESCE(SUM(cu.monto_cuota - cu.total_pagado), 0) - e.saldo_deudor) > 5.00 THEN 'SALDO DIFERENTE'
--         ELSE 'TODO COINCIDE'
--     END AS estado
-- FROM datos_excel_temp e
-- LEFT JOIN clientes c ON e.cedula = c.cedula
-- LEFT JOIN prestamos p ON e.cedula = p.cedula 
--     AND ABS(p.total_financiamiento - e.total_financiamiento) < 100
-- LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
-- GROUP BY e.cedula, e.cliente, e.total_financiamiento, e.abonos, e.saldo_deudor, c.id, p.id, p.total_financiamiento
-- ORDER BY e.cedula;



