-- ============================================================
-- SCRIPT PARA VERIFICAR MODELO ML IMPAGO ACTIVO
-- ============================================================
-- Este script verifica si hay un modelo activo y muestra
-- información detallada sobre el modelo y su archivo
-- ============================================================

-- 1. Verificar si hay un modelo activo
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM modelos_impago_cuotas WHERE activo = true
        ) 
        THEN '✅ HAY MODELO ACTIVO'
        ELSE '❌ NO HAY MODELO ACTIVO'
    END AS estado_modelo;

-- 2. Mostrar información del modelo activo (si existe)
SELECT 
    id,
    nombre,
    version,
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
    ruta_archivo,
    entrenado_en,
    activado_en
FROM modelos_impago_cuotas
ORDER BY entrenado_en DESC;

-- 5. Verificar si hay múltiples modelos activos (debería haber solo uno)
SELECT 
    COUNT(*) AS modelos_activos_count
FROM modelos_impago_cuotas
WHERE activo = true;

