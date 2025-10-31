-- ============================================
-- ELIMINAR DATOS DE PRUEBA (PRÉSTAMOS DE PRUEBA)
-- ============================================
-- Fecha: 2025-10-31
-- Descripción: Elimina préstamos de prueba identificados por cédulas específicas
-- ============================================

-- ============================================
-- PASO 1: VERIFICAR QUÉ SE VA A ELIMINAR
-- ============================================
SELECT 
    'PRESTAMOS DE PRUEBA' AS tipo,
    COUNT(*) AS cantidad_prestamos,
    COUNT(DISTINCT cedula) AS cedulas_unicas,
    SUM(numero_cuotas) AS total_cuotas_esperadas
FROM public.prestamos
WHERE cedula IN ('J12345678', 'E66666666');

-- Listar préstamos que se eliminarán
SELECT 
    id,
    cedula,
    nombres,
    estado,
    total_financiamiento,
    numero_cuotas,
    fecha_registro
FROM public.prestamos
WHERE cedula IN ('J12345678', 'E66666666')
ORDER BY id;

-- Verificar cuotas asociadas
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    COUNT(c.id) AS cuotas_asociadas
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE p.cedula IN ('J12345678', 'E66666666')
GROUP BY p.id, p.cedula, p.nombres
ORDER BY p.id;

-- Verificar pagos asociados
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    COUNT(pa.id) AS pagos_asociados
FROM public.prestamos p
LEFT JOIN public.pagos pa ON pa.prestamo_id = p.id
WHERE p.cedula IN ('J12345678', 'E66666666')
GROUP BY p.id, p.cedula
ORDER BY p.id;

-- ============================================
-- PASO 2: ELIMINAR EN ORDEN CORRECTO
-- ============================================
-- IMPORTANTE: Ejecutar esto en una transacción para poder hacer ROLLBACK si es necesario

BEGIN;

-- 2.1 Contar cuotas que se eliminarán (ANTES de eliminar)
SELECT 'Cuotas a eliminar' AS operacion, COUNT(*) AS cantidad
FROM public.cuotas c
INNER JOIN public.prestamos p ON p.id = c.prestamo_id
WHERE p.cedula IN ('J12345678', 'E66666666');

-- 2.2 Eliminar cuotas asociadas a préstamos de prueba
DELETE FROM public.cuotas
WHERE prestamo_id IN (
    SELECT id FROM public.prestamos 
    WHERE cedula IN ('J12345678', 'E66666666')
);

-- 2.3 Eliminar pagos asociados a préstamos de prueba (OPCIONAL)
-- Descomentar si también quieres eliminar los pagos
/*
DELETE FROM public.pagos
WHERE prestamo_id IN (
    SELECT id FROM public.prestamos 
    WHERE cedula IN ('J12345678', 'E66666666')
);
*/

-- 2.4 Eliminar los préstamos de prueba
DELETE FROM public.prestamos
WHERE cedula IN ('J12345678', 'E66666666');

-- Verificar eliminación
SELECT 
    'RESUMEN FINAL' AS tipo,
    COUNT(*) AS prestamos_restantes_con_cedulas_prueba
FROM public.prestamos
WHERE cedula IN ('J12345678', 'E66666666');

-- ============================================
-- PASO 3: CONFIRMAR O REVERTIR
-- ============================================
-- Si todo está correcto, ejecutar:
-- COMMIT;

-- Si hay algún problema, ejecutar:
-- ROLLBACK;

-- ============================================
-- PASO 4: VERIFICACIÓN FINAL
-- ============================================
-- Ejecutar DESPUÉS del COMMIT
SELECT 
    'VERIFICACIÓN FINAL' AS tipo,
    COUNT(*) AS total_prestamos_restantes,
    COUNT(CASE WHEN cedula = 'J12345678' THEN 1 END) AS con_cedula_J12345678,
    COUNT(CASE WHEN cedula = 'E66666666' THEN 1 END) AS con_cedula_E66666666
FROM public.prestamos;

-- Verificar que no queden cuotas huérfanas
SELECT 
    'CUOTAS HUÉRFANAS' AS tipo,
    COUNT(*) AS cantidad
FROM public.cuotas c
WHERE NOT EXISTS (
    SELECT 1 FROM public.prestamos p 
    WHERE p.id = c.prestamo_id
);

-- ============================================
-- NOTAS IMPORTANTES
-- ============================================
-- 
-- 1. Este script elimina préstamos con cédulas:
--    - 'J12345678' (Juan García - datos de prueba)
--    - 'E66666666' (Corpocalza Sa - datos de prueba)
--
-- 2. Se eliminan en este orden:
--    - Cuotas asociadas (obligatorio)
--    - Pagos asociados (opcional, comentado)
--    - Préstamos (obligatorio)
--
-- 3. El script está en una TRANSACCIÓN (BEGIN)
--    - Debes ejecutar COMMIT para confirmar
--    - O ROLLBACK para revertir todos los cambios
--
-- 4. Si necesitas eliminar otros datos de prueba, agrega
--    las cédulas al IN clause: cedula IN ('CEDULA1', 'CEDULA2', ...)
--
-- ============================================

