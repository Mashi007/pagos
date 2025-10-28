-- ============================================
-- CORRECCIÓN: Restaurar 12 cuotas en préstamos afectados
-- ============================================
-- Este script corrige los préstamos que se aprobaron con 36 cuotas
-- cuando deberían tener 12 cuotas

-- PASO 1: Verificar qué préstamos se afectaron
SELECT 
    id,
    cedula,
    nombres,
    numero_cuotas,
    estado,
    created_at
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'
    AND numero_cuotas != 12  -- No debería tener 36
ORDER BY 
    id DESC
LIMIT 10;

-- PASO 2: Eliminar cuotas incorrectas
-- Ejecutar SOLO para los préstamos que tienen 36 cuotas cuando deberían tener 12
DELETE FROM cuotas
WHERE prestamo_id IN (
    SELECT id FROM prestamos 
    WHERE estado = 'APROBADO' AND numero_cuotas = 36
);

-- PASO 3: Corregir numero_cuotas a 12 para préstamos afectados
UPDATE prestamos
SET 
    numero_cuotas = 12,
    cuota_periodo = total_financiamiento / 12.0
WHERE 
    estado = 'APROBADO' 
    AND numero_cuotas = 36;

-- PASO 4: Verificar corrección
SELECT 
    id,
    nombres,
    numero_cuotas,
    cuota_periodo,
    estado
FROM 
    prestamos
WHERE 
    id IN (9, 10, 11)  -- Ajustar IDs según tus préstamos
ORDER BY 
    id;

-- PASO 5: Regenerar tabla de amortización (12 cuotas)
-- Este paso lo haremos desde el frontend o API
-- 
-- Para cada préstamo afectado, ejecutar en Postman/API:
-- POST /api/v1/prestamos/{prestamo_id}/generar-amortizacion

-- ============================================
-- NOTAS IMPORTANTES
-- ============================================
-- 
-- 1. Ejecuta este script SOLO si has aprobado préstamos
--    con 36 cuotas cuando deberían tener 12
-- 
-- 2. Después de ejecutar, necesitas regenerar las cuotas
--    desde la API o el frontend
-- 
-- 3. Los cambios ya guardados en el frontend persistirán
--    hasta que recargues la página
-- 
-- ============================================

