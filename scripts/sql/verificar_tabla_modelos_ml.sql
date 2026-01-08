-- ============================================================
-- SCRIPT PARA VERIFICAR TABLA DE MODELOS ML IMPAGO
-- ============================================================
-- Este script verifica si existe la tabla modelos_impago_cuotas
-- y muestra información sobre los modelos almacenados
-- ============================================================

-- 1. Verificar si la tabla existe
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'modelos_impago_cuotas'
        ) 
        THEN '✅ La tabla modelos_impago_cuotas EXISTE'
        ELSE '❌ La tabla modelos_impago_cuotas NO EXISTE'
    END AS estado_tabla;

-- 2. Mostrar estructura de la tabla (si existe)
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
    AND table_name = 'modelos_impago_cuotas'
ORDER BY ordinal_position;

-- 3. Contar total de modelos
SELECT 
    COUNT(*) AS total_modelos,
    COUNT(CASE WHEN activo = true THEN 1 END) AS modelos_activos,
    COUNT(CASE WHEN activo = false THEN 1 END) AS modelos_inactivos
FROM modelos_impago_cuotas;

-- 4. Listar todos los modelos con información básica
SELECT 
    id,
    nombre,
    algoritmo,
    activo,
    accuracy,
    f1_score,
    ruta_archivo,
    entrenado_en,
    activado_en
FROM modelos_impago_cuotas
ORDER BY entrenado_en DESC;

-- 5. Mostrar modelo activo (si existe)
SELECT 
    id,
    nombre,
    algoritmo,
    accuracy,
    precision,
    recall,
    f1_score,
    roc_auc,
    ruta_archivo,
    total_datos_entrenamiento,
    total_datos_test,
    activo,
    entrenado_en,
    activado_en,
    descripcion
FROM modelos_impago_cuotas
WHERE activo = true
ORDER BY activado_en DESC NULLS LAST, entrenado_en DESC
LIMIT 1;

-- 6. Verificar si el archivo del modelo existe (solo información, no verifica el sistema de archivos)
SELECT 
    id,
    nombre,
    ruta_archivo,
    CASE 
        WHEN ruta_archivo LIKE 'ml_models/%' THEN 'Ruta relativa (ml_models/)'
        WHEN ruta_archivo LIKE '/%' THEN 'Ruta absoluta'
        ELSE 'Ruta relativa (directorio actual)'
    END AS tipo_ruta,
    activo
FROM modelos_impago_cuotas
WHERE activo = true;

-- 7. Resumen de modelos por algoritmo
SELECT 
    algoritmo,
    COUNT(*) AS cantidad,
    COUNT(CASE WHEN activo = true THEN 1 END) AS activos,
    AVG(accuracy) AS accuracy_promedio,
    AVG(f1_score) AS f1_promedio,
    MAX(entrenado_en) AS ultimo_entrenamiento
FROM modelos_impago_cuotas
GROUP BY algoritmo
ORDER BY cantidad DESC;

-- 8. Modelos más recientes (últimos 5)
SELECT 
    id,
    nombre,
    algoritmo,
    activo,
    accuracy,
    f1_score,
    ruta_archivo,
    entrenado_en
FROM modelos_impago_cuotas
ORDER BY entrenado_en DESC
LIMIT 5;

