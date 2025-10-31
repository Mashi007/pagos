-- ============================================
-- ELIMINAR DATOS DE PRUEBA - VERSIÓN DIRECTA
-- ============================================
-- Ejecuta este script completo en DBeaver
-- Elimina préstamos de prueba con cédulas: J12345678 y E66666666
-- ============================================

BEGIN;

-- 1. Eliminar cuotas asociadas
DELETE FROM public.cuotas
WHERE prestamo_id IN (
    SELECT id FROM public.prestamos 
    WHERE cedula IN ('J12345678', 'E66666666')
);

-- 2. Eliminar pagos asociados (opcional - descomentar si quieres eliminar pagos también)
-- DELETE FROM public.pagos
-- WHERE prestamo_id IN (
--     SELECT id FROM public.prestamos 
--     WHERE cedula IN ('J12345678', 'E66666666')
-- );

-- 3. Eliminar los préstamos
DELETE FROM public.prestamos
WHERE cedula IN ('J12345678', 'E66666666');

-- 4. Verificar que se eliminaron
SELECT 
    COUNT(*) AS prestamos_restantes_con_cedulas_prueba
FROM public.prestamos
WHERE cedula IN ('J12345678', 'E66666666');

-- Si el resultado anterior es 0, entonces todo está bien
-- Ejecuta COMMIT para confirmar
COMMIT;

-- Si hubo algún problema, ejecuta ROLLBACK en lugar de COMMIT

