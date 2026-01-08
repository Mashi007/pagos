-- ============================================================
-- SCRIPT PARA CORREGIR MODELOS ML IMPAGO ACTIVOS
-- ============================================================
-- Este script asegura que solo haya UN modelo activo
-- Si hay múltiples activos, desactiva todos excepto el más reciente
-- ============================================================

-- 1. Ver cuántos modelos están activos actualmente
SELECT 
    COUNT(*) AS total_activos,
    STRING_AGG(id::text, ', ') AS ids_activos
FROM modelos_impago_cuotas
WHERE activo = true;

-- 2. Ver detalles de los modelos activos
SELECT 
    id,
    nombre,
    activo,
    entrenado_en,
    activado_en,
    ruta_archivo
FROM modelos_impago_cuotas
WHERE activo = true
ORDER BY activado_en DESC NULLS LAST, entrenado_en DESC;

-- 3. CORREGIR: Desactivar todos excepto el más reciente
-- (Descomenta las siguientes líneas para ejecutar)

-- BEGIN;
-- 
-- -- Desactivar todos los modelos
-- UPDATE modelos_impago_cuotas
-- SET activo = false
-- WHERE activo = true;
-- 
-- -- Activar solo el más reciente (el que tiene activado_en más reciente, o si es NULL, el entrenado más reciente)
-- UPDATE modelos_impago_cuotas
-- SET activo = true,
--     activado_en = NOW()
-- WHERE id = (
--     SELECT id
--     FROM modelos_impago_cuotas
--     ORDER BY 
--         COALESCE(activado_en, '1970-01-01'::timestamp) DESC,
--         entrenado_en DESC
--     LIMIT 1
-- );
-- 
-- COMMIT;

-- 4. Verificar resultado
SELECT 
    id,
    nombre,
    activo,
    entrenado_en,
    activado_en
FROM modelos_impago_cuotas
ORDER BY activo DESC, entrenado_en DESC;

