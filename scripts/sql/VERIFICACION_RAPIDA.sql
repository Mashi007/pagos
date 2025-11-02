-- ============================================
-- VERIFICACIÓN RÁPIDA
-- ============================================
-- Verificación básica después de aplicar defaults
-- ============================================

-- Total de registros
SELECT 
    COUNT(*) AS total_registros,
    3681 AS esperados,
    CASE 
        WHEN COUNT(*) = 3681 THEN '✅ CORRECTO'
        ELSE '⚠️ INCORRECTO'
    END AS estado
FROM public.prestamos_staging;

-- Campos fundamentales
SELECT 
    COUNT(*) AS total,
    COUNT(CASE WHEN cedula IS NULL OR TRIM(cedula) = '' THEN 1 END) AS sin_cedula,
    COUNT(CASE WHEN concesionario IS NULL OR TRIM(concesionario) = '' THEN 1 END) AS sin_concesionario,
    COUNT(CASE WHEN analista IS NULL OR TRIM(analista) = '' THEN 1 END) AS sin_analista,
    COUNT(CASE WHEN modelo_vehiculo IS NULL OR TRIM(modelo_vehiculo) = '' THEN 1 END) AS sin_modelo_vehiculo,
    CASE 
        WHEN COUNT(CASE WHEN cedula IS NULL OR TRIM(cedula) = '' THEN 1 END) = 0
         AND COUNT(CASE WHEN concesionario IS NULL OR TRIM(concesionario) = '' THEN 1 END) = 0
         AND COUNT(CASE WHEN analista IS NULL OR TRIM(analista) = '' THEN 1 END) = 0
         AND COUNT(CASE WHEN modelo_vehiculo IS NULL OR TRIM(modelo_vehiculo) = '' THEN 1 END) = 0
        THEN '✅ LISTO PARA MIGRAR'
        ELSE '⚠️ HAY CAMPOS VACÍOS'
    END AS estado
FROM public.prestamos_staging;

