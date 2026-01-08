-- ======================================================================
-- SCRIPT COMPLETO PARA RESTAURAR PRESTAMOS ELIMINADOS
-- ======================================================================
-- IMPORTANTE: 
--   1. Hacer backup completo antes de ejecutar
--   2. Este script restaura préstamos con información de cliente temporal
--   3. Los campos de cliente deben corregirse manualmente después
-- ======================================================================

-- ======================================================================
-- PASO 1: Crear tabla temporal con información de préstamos a restaurar
-- ======================================================================

CREATE TEMP TABLE prestamos_a_restaurar_temp AS
WITH prestamos_info AS (
    SELECT 
        c.prestamo_id,
        COUNT(*) AS numero_cuotas,
        MIN(c.fecha_vencimiento) AS fecha_base_calculo,
        MAX(c.fecha_vencimiento) AS ultima_fecha,
        SUM(c.monto_capital) AS total_financiamiento,
        SUM(c.monto_interes) AS total_interes,
        AVG(c.monto_cuota) AS cuota_periodo,
        SUM(c.total_pagado) AS total_pagado,
        CASE 
            WHEN MAX(c.fecha_vencimiento) IS NOT NULL 
                 AND MIN(c.fecha_vencimiento) IS NOT NULL 
                 AND COUNT(*) > 1 THEN
                CASE 
                    WHEN (MAX(c.fecha_vencimiento) - MIN(c.fecha_vencimiento)) / (COUNT(*) - 1) BETWEEN 25 AND 35 THEN 'MENSUAL'
                    WHEN (MAX(c.fecha_vencimiento) - MIN(c.fecha_vencimiento)) / (COUNT(*) - 1) BETWEEN 12 AND 18 THEN 'QUINCENAL'
                    WHEN (MAX(c.fecha_vencimiento) - MIN(c.fecha_vencimiento)) / (COUNT(*) - 1) BETWEEN 5 AND 9 THEN 'SEMANAL'
                    ELSE 'MENSUAL'
                END
            ELSE 'MENSUAL'
        END AS modalidad_pago,
        CASE 
            WHEN SUM(c.monto_interes) > 0 AND SUM(c.monto_capital) > 0 THEN
                ROUND((SUM(c.monto_interes) / SUM(c.monto_capital)) * 100, 2)
            ELSE 0.00
        END AS tasa_interes_estimada
    FROM cuotas c
    LEFT JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.id IS NULL
      AND SUM(c.monto_capital) > 0  -- Solo préstamos con capital válido
    GROUP BY c.prestamo_id
)
SELECT 
    prestamo_id AS prestamo_id_original,
    numero_cuotas,
    fecha_base_calculo,
    total_financiamiento,
    cuota_periodo,
    modalidad_pago,
    tasa_interes_estimada,
    total_pagado
FROM prestamos_info
WHERE total_financiamiento > 0
ORDER BY prestamo_id;

-- ======================================================================
-- PASO 2: Verificar información antes de restaurar
-- ======================================================================

SELECT 
    'INFORMACION A RESTAURAR' AS tipo,
    COUNT(*) AS total_prestamos,
    SUM(numero_cuotas) AS total_cuotas,
    SUM(total_financiamiento) AS total_financiamiento,
    SUM(total_pagado) AS total_pagado
FROM prestamos_a_restaurar_temp;

-- Ver primeros 10 préstamos a restaurar
SELECT 
    prestamo_id_original,
    numero_cuotas,
    fecha_base_calculo,
    total_financiamiento,
    cuota_periodo,
    modalidad_pago,
    tasa_interes_estimada
FROM prestamos_a_restaurar_temp
ORDER BY prestamo_id_original
LIMIT 10;

-- ======================================================================
-- PASO 3: Obtener próximo ID disponible (si vamos a usar IDs nuevos)
-- ======================================================================

SELECT 
    'PROXIMO ID DISPONIBLE' AS tipo,
    COALESCE(MAX(id), 0) + 1 AS proximo_id
FROM prestamos;

-- ======================================================================
-- PASO 4: Restaurar préstamos con información temporal de cliente
-- ======================================================================
-- NOTA: Los campos cliente_id, cedula y nombres son temporales
--       Deben corregirse manualmente después de la restauración

-- Crear cliente temporal si no existe (para préstamos sin cliente)
INSERT INTO clientes (cedula, nombres, activo, fecha_registro)
SELECT 
    'TEMP_' || prestamo_id_original::TEXT AS cedula,
    'CLIENTE TEMPORAL PRESTAMO ' || prestamo_id_original::TEXT AS nombres,
    FALSE AS activo,
    CURRENT_TIMESTAMP AS fecha_registro
FROM prestamos_a_restaurar_temp
WHERE NOT EXISTS (
    SELECT 1 FROM clientes 
    WHERE cedula = 'TEMP_' || prestamos_a_restaurar_temp.prestamo_id_original::TEXT
)
ON CONFLICT DO NOTHING;

-- Restaurar préstamos
INSERT INTO prestamos (
    id,
    cliente_id,
    cedula,
    nombres,
    total_financiamiento,
    modalidad_pago,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    fecha_base_calculo,
    estado,
    fecha_registro,
    fecha_actualizacion,
    fecha_aprobacion,
    usuario_proponente,
    usuario_aprobador,
    producto,
    producto_financiero,
    observaciones
)
SELECT 
    pr.prestamo_id_original AS id,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    pr.total_financiamiento,
    pr.modalidad_pago,
    pr.numero_cuotas,
    pr.cuota_periodo,
    pr.tasa_interes_estimada AS tasa_interes,
    pr.fecha_base_calculo,
    'APROBADO' AS estado,
    pr.fecha_base_calculo::TIMESTAMP AS fecha_registro,  -- Usar fecha_base_calculo como fecha_registro
    CURRENT_TIMESTAMP AS fecha_actualizacion,
    pr.fecha_base_calculo::TIMESTAMP AS fecha_aprobacion,  -- Usar fecha_base_calculo como fecha_aprobacion
    'sistema@restauracion.com' AS usuario_proponente,
    'sistema@restauracion.com' AS usuario_aprobador,
    'RESTAURADO DESDE CUOTAS' AS producto,
    'RESTAURADO DESDE CUOTAS' AS producto_financiero,
    'Préstamo restaurado automáticamente desde cuotas huérfanas. Información de cliente temporal - REQUIERE CORRECCION.' AS observaciones
FROM prestamos_a_restaurar_temp pr
LEFT JOIN clientes c ON c.cedula = 'TEMP_' || pr.prestamo_id_original::TEXT
WHERE NOT EXISTS (
    SELECT 1 FROM prestamos WHERE id = pr.prestamo_id_original
)
ORDER BY pr.prestamo_id_original;

-- ======================================================================
-- PASO 5: Verificar restauración
-- ======================================================================

SELECT 
    'PRESTAMOS RESTAURADOS' AS tipo,
    COUNT(*) AS total_restaurados
FROM prestamos
WHERE producto = 'RESTAURADO DESDE CUOTAS';

-- Verificar que las cuotas ahora tienen préstamo válido
SELECT 
    'CUOTAS CON PRESTAMO VALIDO' AS tipo,
    COUNT(*) AS total_cuotas_con_prestamo
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.producto = 'RESTAURADO DESDE CUOTAS';

-- Verificar cuotas huérfanas restantes
SELECT 
    'CUOTAS HUERFANAS RESTANTES' AS tipo,
    COUNT(*) AS total_cuotas_huerfanas
FROM cuotas c
LEFT JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.id IS NULL;

-- ======================================================================
-- PASO 6: Listar préstamos restaurados que requieren corrección
-- ======================================================================

SELECT 
    'PRESTAMOS QUE REQUIEREN CORRECCION' AS tipo,
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.cliente_id,
    COUNT(c.id) AS total_cuotas,
    SUM(c.total_pagado) AS total_pagado
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.producto = 'RESTAURADO DESDE CUOTAS'
GROUP BY p.id, p.cedula, p.nombres, p.cliente_id
ORDER BY p.id
LIMIT 20;

-- ======================================================================
-- PASO 7: Limpiar tabla temporal
-- ======================================================================

DROP TABLE IF EXISTS prestamos_a_restaurar_temp;

-- ======================================================================
-- NOTAS FINALES:
-- ======================================================================
-- 1. Los préstamos restaurados tienen información temporal de cliente
-- 2. Debes corregir manualmente:
--    - cliente_id (buscar cliente real por cédula si existe)
--    - cedula (cédula real del cliente)
--    - nombres (nombre real del cliente)
-- 3. Si el cliente no existe, créalo primero en la tabla clientes
-- 4. Después de corregir, actualiza el préstamo:
--    UPDATE prestamos 
--    SET cliente_id = <cliente_id_real>,
--        cedula = <cedula_real>,
--        nombres = <nombres_reales>,
--        observaciones = 'Préstamo restaurado - información corregida'
--    WHERE id = <prestamo_id>;
-- ======================================================================
