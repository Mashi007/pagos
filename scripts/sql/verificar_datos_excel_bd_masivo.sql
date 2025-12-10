-- ============================================
-- VERIFICACIÓN MASIVA: Comparar Excel con BD
-- ============================================
-- 
-- Este script permite verificar múltiples registros del Excel
-- creando una tabla temporal e insertando los datos.
--
-- INSTRUCCIONES:
-- 1. Convierte tu Excel a CSV
-- 2. Copia los datos y pégalos en la sección INSERT
-- 3. Ajusta los nombres de columnas si es necesario
-- 4. Ejecuta el script completo
--
-- ============================================

-- Crear tabla temporal con estructura del Excel
CREATE TEMP TABLE IF NOT EXISTS datos_excel (
    cliente VARCHAR(200),
    cedula VARCHAR(20),
    fecha_no VARCHAR(50),
    monto_cancelado_cuota NUMERIC(12,2),
    total_financiamiento NUMERIC(12,2),
    abonos NUMERIC(12,2),
    saldo_deudor NUMERIC(12,2),
    fecha_entrega VARCHAR(50),
    cuotas INTEGER,
    modalidad_financiamiento VARCHAR(50)
);

-- ============================================
-- INSERTAR DATOS DEL EXCEL AQUÍ
-- ============================================
-- 
-- Reemplaza esto con tus datos del Excel (convertido a CSV)
-- Formato: INSERT INTO datos_excel VALUES
-- ('Cliente1', 'V12345678', '14-oct-24', 48.00, 864.00, 630.00, 234.00, '18-oct', 18, 'QUINCENAL'),
-- ('Cliente2', 'V87654321', '15-oct-24', 96.00, 1152.00, 500.00, 652.00, '20-oct', 12, 'MENSUAL'),
-- ... (todos tus registros)
-- ;

-- Ejemplo con el registro mostrado:
INSERT INTO datos_excel VALUES
('YOLMER SAUL SUAREZ', 'V23107415', '14-oct-24', 48.00, 864.00, 630.00, 234.00, '18-oct', 18, 'QUINCENAL');

-- ============================================
-- VERIFICACIÓN MASIVA
-- ============================================

-- RESUMEN: Clientes que existen vs no existen
SELECT 
    'RESUMEN CLIENTES' AS tipo,
    COUNT(*) AS total_registros_excel,
    COUNT(c.id) AS clientes_existentes,
    COUNT(*) - COUNT(c.id) AS clientes_faltantes,
    ROUND(COUNT(c.id) * 100.0 / COUNT(*), 2) AS porcentaje_existentes
FROM datos_excel e
LEFT JOIN clientes c ON e.cedula = c.cedula;

-- RESUMEN: Préstamos que existen vs no existen
SELECT 
    'RESUMEN PRESTAMOS' AS tipo,
    COUNT(*) AS total_registros_excel,
    COUNT(p.id) AS prestamos_existentes,
    COUNT(*) - COUNT(p.id) AS prestamos_faltantes,
    ROUND(COUNT(p.id) * 100.0 / COUNT(*), 2) AS porcentaje_existentes
FROM datos_excel e
LEFT JOIN prestamos p ON e.cedula = p.cedula 
    AND ABS(p.total_financiamiento - e.total_financiamiento) < 10;

-- COMPARACIÓN DETALLADA: Todos los registros
SELECT 
    'COMPARACION DETALLADA' AS tipo,
    e.cedula AS cedula_excel,
    e.cliente AS cliente_excel,
    e.total_financiamiento AS total_financiamiento_excel,
    e.abonos AS abonos_excel,
    e.saldo_deudor AS saldo_deudor_excel,
    e.cuotas AS cuotas_excel,
    e.modalidad_financiamiento AS modalidad_excel,
    c.id AS cliente_id_bd,
    CASE WHEN c.id IS NULL THEN 'NO EXISTE' ELSE 'EXISTE' END AS cliente_estado,
    p.id AS prestamo_id_bd,
    CASE WHEN p.id IS NULL THEN 'NO EXISTE' ELSE 'EXISTE' END AS prestamo_estado,
    p.total_financiamiento AS total_financiamiento_bd,
    CASE 
        WHEN p.id IS NULL THEN 'PRESTAMO NO EXISTE'
        WHEN ABS(p.total_financiamiento - e.total_financiamiento) > 0.01 THEN 'DIFERENTE'
        ELSE 'COINCIDE'
    END AS total_financiamiento_estado,
    COALESCE(SUM(cu.total_pagado), 0) AS abonos_bd,
    CASE 
        WHEN p.id IS NULL THEN 'PRESTAMO NO EXISTE'
        WHEN ABS(COALESCE(SUM(cu.total_pagado), 0) - e.abonos) > 0.01 THEN 'DIFERENTE'
        ELSE 'COINCIDE'
    END AS abonos_estado,
    COALESCE(SUM(cu.monto_cuota - cu.total_pagado), 0) AS saldo_deudor_bd,
    CASE 
        WHEN p.id IS NULL THEN 'PRESTAMO NO EXISTE'
        WHEN ABS(COALESCE(SUM(cu.monto_cuota - cu.total_pagado), 0) - e.saldo_deudor) > 5.00 THEN 'DIFERENTE'
        ELSE 'COINCIDE'
    END AS saldo_deudor_estado,
    COUNT(cu.id) AS cuotas_generadas_bd,
    CASE 
        WHEN p.id IS NULL THEN 'PRESTAMO NO EXISTE'
        WHEN COUNT(cu.id) != e.cuotas THEN 'DIFERENTE'
        ELSE 'COINCIDE'
    END AS cuotas_estado,
    p.modalidad_pago AS modalidad_bd,
    CASE 
        WHEN p.id IS NULL THEN 'PRESTAMO NO EXISTE'
        WHEN UPPER(COALESCE(p.modalidad_pago, '')) != UPPER(e.modalidad_financiamiento) THEN 'DIFERENTE'
        ELSE 'COINCIDE'
    END AS modalidad_estado
FROM datos_excel e
LEFT JOIN clientes c ON e.cedula = c.cedula
LEFT JOIN prestamos p ON e.cedula = p.cedula 
    AND ABS(p.total_financiamiento - e.total_financiamiento) < 10
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
GROUP BY e.cedula, e.cliente, e.total_financiamiento, e.abonos, e.saldo_deudor, 
         e.cuotas, e.modalidad_financiamiento, c.id, p.id, p.total_financiamiento, p.modalidad_pago
ORDER BY 
    CASE WHEN c.id IS NULL THEN 1 ELSE 0 END,
    CASE WHEN p.id IS NULL THEN 1 ELSE 0 END,
    e.cedula;

-- REGISTROS CON PROBLEMAS
SELECT 
    'REGISTROS CON PROBLEMAS' AS tipo,
    e.cedula,
    e.cliente,
    CASE 
        WHEN c.id IS NULL THEN 'CLIENTE NO EXISTE'
        WHEN p.id IS NULL THEN 'PRESTAMO NO EXISTE'
        WHEN ABS(p.total_financiamiento - e.total_financiamiento) > 0.01 THEN 'TOTAL FINANCIAMIENTO DIFERENTE'
        WHEN ABS(COALESCE(SUM(cu.total_pagado), 0) - e.abonos) > 0.01 THEN 'ABONOS DIFERENTES'
        WHEN ABS(COALESCE(SUM(cu.monto_cuota - cu.total_pagado), 0) - e.saldo_deudor) > 5.00 THEN 'SALDO DEUDOR DIFERENTE'
        WHEN COUNT(cu.id) != e.cuotas THEN 'NUMERO CUOTAS DIFERENTE'
        WHEN UPPER(COALESCE(p.modalidad_pago, '')) != UPPER(e.modalidad_financiamiento) THEN 'MODALIDAD DIFERENTE'
        ELSE 'SIN PROBLEMAS'
    END AS problema,
    e.total_financiamiento AS total_excel,
    p.total_financiamiento AS total_bd,
    e.abonos AS abonos_excel,
    COALESCE(SUM(cu.total_pagado), 0) AS abonos_bd,
    e.saldo_deudor AS saldo_excel,
    COALESCE(SUM(cu.monto_cuota - cu.total_pagado), 0) AS saldo_bd
FROM datos_excel e
LEFT JOIN clientes c ON e.cedula = c.cedula
LEFT JOIN prestamos p ON e.cedula = p.cedula 
    AND ABS(p.total_financiamiento - e.total_financiamiento) < 10
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
GROUP BY e.cedula, e.cliente, e.total_financiamiento, e.abonos, e.saldo_deudor, 
         e.cuotas, e.modalidad_financiamiento, c.id, p.id, p.total_financiamiento, p.modalidad_pago
HAVING 
    c.id IS NULL 
    OR p.id IS NULL 
    OR ABS(p.total_financiamiento - e.total_financiamiento) > 0.01
    OR ABS(COALESCE(SUM(cu.total_pagado), 0) - e.abonos) > 0.01
    OR ABS(COALESCE(SUM(cu.monto_cuota - cu.total_pagado), 0) - e.saldo_deudor) > 5.00
    OR COUNT(cu.id) != e.cuotas
    OR UPPER(COALESCE(p.modalidad_pago, '')) != UPPER(e.modalidad_financiamiento)
ORDER BY problema, e.cedula;

-- Limpiar tabla temporal
-- DROP TABLE IF EXISTS datos_excel;



