-- ============================================
-- VERIFICAR IMPORTACIÓN COMPLETA
-- ============================================
-- 
-- Después de importar, verificar cuántos registros
-- se importaron correctamente
--
-- ============================================

-- 1. Total de registros importados
SELECT 
    'TOTAL REGISTROS IMPORTADOS' AS tipo,
    COUNT(*) AS total_registros
FROM bd_clientes_csv;

-- 2. Verificar datos válidos
SELECT 
    'REGISTROS VÁLIDOS' AS tipo,
    COUNT(*) AS total_validos,
    COUNT(CASE WHEN "CLIENTE" IS NOT NULL THEN 1 END) AS con_cliente,
    COUNT(CASE WHEN "CEDULA IDENTIDAD" IS NOT NULL THEN 1 END) AS con_cedula,
    COUNT(CASE WHEN "TOTAL FINANCIAMIENTO" IS NOT NULL THEN 1 END) AS con_total,
    COUNT(CASE WHEN "MONTO CANCELADO CUOTA" IS NOT NULL THEN 1 END) AS con_monto_cuota
FROM bd_clientes_csv;

-- 3. Muestra de datos
SELECT 
    'MUESTRA DE DATOS' AS tipo,
    "CLIENTE",
    "CEDULA IDENTIDAD",
    "TOTAL FINANCIAMIENTO",
    "MONTO CANCELADO CUOTA",
    "MODALIDAD FINANCIAMIENTO"
FROM bd_clientes_csv
LIMIT 10;

-- 4. Estadísticas de valores
SELECT 
    'ESTADÍSTICAS' AS tipo,
    MIN("TOTAL FINANCIAMIENTO") AS min_total,
    MAX("TOTAL FINANCIAMIENTO") AS max_total,
    AVG("TOTAL FINANCIAMIENTO") AS avg_total,
    MIN("MONTO CANCELADO CUOTA") AS min_cuota,
    MAX("MONTO CANCELADO CUOTA") AS max_cuota,
    AVG("MONTO CANCELADO CUOTA") AS avg_cuota
FROM bd_clientes_csv
WHERE "TOTAL FINANCIAMIENTO" IS NOT NULL
  AND "MONTO CANCELADO CUOTA" IS NOT NULL;

