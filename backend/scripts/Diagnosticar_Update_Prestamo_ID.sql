-- ============================================
-- DIAGNÓSTICO: Por qué el UPDATE no actualizó registros
-- ============================================

-- 1. Verificar cuántos pagos tienen prestamo_id NULL
SELECT 
    COUNT(*) as total_pagos_prestamo_id_null,
    'Pagos con prestamo_id IS NULL' as descripcion
FROM pagos
WHERE prestamo_id IS NULL;

-- 2. Verificar si esos pagos tienen clientes con préstamos aprobados
SELECT 
    COUNT(*) as pagos_candidatos,
    'Pagos que cumplen condiciones del UPDATE' as descripcion
FROM pagos p
WHERE p.prestamo_id IS NULL
AND EXISTS (
    SELECT 1 
    FROM prestamos pr 
    WHERE pr.cedula = p.cedula_cliente 
    AND pr.estado = 'APROBADO'
);

-- 3. Verificar nombres de columnas y estructura
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'pagos'
AND column_name IN ('prestamo_id', 'cedula_cliente')
ORDER BY column_name;

SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'prestamos'
AND column_name IN ('id', 'cedula', 'estado')
ORDER BY column_name;

-- 4. Probar la subconsulta SELECT que usa el UPDATE
SELECT 
    p.id as pago_id,
    p.cedula_cliente,
    p.prestamo_id as prestamo_id_actual,
    (SELECT pr.id 
     FROM prestamos pr 
     WHERE pr.cedula = p.cedula_cliente 
     AND pr.estado = 'APROBADO'
     ORDER BY pr.id
     LIMIT 1) as prestamo_id_que_se_asignaria
FROM pagos p
WHERE p.prestamo_id IS NULL
AND EXISTS (
    SELECT 1 
    FROM prestamos pr 
    WHERE pr.cedula = p.cedula_cliente 
    AND pr.estado = 'APROBADO'
)
LIMIT 10;

-- 5. Verificar valores de estado en prestamos
SELECT DISTINCT estado, COUNT(*) as cantidad
FROM prestamos
GROUP BY estado
ORDER BY cantidad DESC;

-- 6. Verificar si hay diferencias en el nombre de columna (puede ser prestamo_id vs prestamoId)
SELECT 
    p.id as pago_id,
    p.cedula_cliente,
    p.prestamo_id,
    CASE 
        WHEN p.prestamo_id IS NULL THEN 'ES NULL'
        ELSE 'NO ES NULL'
    END as estado_prestamo_id
FROM pagos p
WHERE p.prestamo_id IS NULL
LIMIT 5;

