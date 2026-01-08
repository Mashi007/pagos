-- ============================================================================
-- SCRIPT DE AUDITORÍA INTEGRAL DE CONFIGURACIÓN AI - VERSIÓN POR SECCIONES
-- Para ejecutar en DBeaver
-- ============================================================================
-- INSTRUCCIONES:
-- 1. Ejecuta cada sección por separado (selecciona y ejecuta)
-- 2. O ejecuta todo el script si todas las tablas existen
-- ============================================================================

-- ============================================================================
-- VERIFICACIÓN INICIAL: EXISTENCIA DE TABLAS
-- ============================================================================
SELECT 
    '=== VERIFICACIÓN DE TABLAS ===' AS tipo,
    'configuracion_sistema' AS tabla,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'configuracion_sistema'
        ) THEN '✅ Existe'
        ELSE '❌ No existe'
    END AS estado

UNION ALL

SELECT 
    'Verificación',
    'documentos_ai',
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'documentos_ai'
        ) THEN '✅ Existe'
        ELSE '❌ No existe (ejecutar migración)'
    END

UNION ALL

SELECT 
    'Verificación',
    'documento_ai_embeddings',
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'documento_ai_embeddings'
        ) THEN '✅ Existe'
        ELSE '⚠️ No existe (opcional - para RAG)'
    END

UNION ALL

SELECT 
    'Verificación',
    'ai_prompt_variables',
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'ai_prompt_variables'
        ) THEN '✅ Existe'
        ELSE '⚠️ No existe (opcional - para prompts personalizados)'
    END;

-- ============================================================================
-- SECCIÓN 1: CONFIGURACIÓN DE AI
-- ============================================================================
-- Ejecutar esta sección si la tabla configuracion_sistema existe
SELECT 
    '=== CONFIGURACIÓN DE AI ===' AS seccion,
    id,
    categoria,
    clave,
    CASE 
        WHEN clave = 'openai_api_key' THEN 
            CASE 
                WHEN valor IS NULL OR valor = '' THEN '❌ NO CONFIGURADO'
                WHEN LENGTH(valor) < 10 THEN '⚠️ VALOR INVÁLIDO (muy corto)'
                WHEN valor NOT LIKE 'sk-%' THEN '⚠️ FORMATO INCORRECTO (debe empezar con sk-)'
                ELSE '✅ CONFIGURADO (' || SUBSTRING(valor, 1, 7) || '...' || SUBSTRING(valor, LENGTH(valor)-4) || ')'
            END
        ELSE valor
    END AS valor,
    tipo_dato,
    CASE 
        WHEN clave = 'activo' THEN valor
        ELSE NULL
    END AS activo,
    creado_en,
    actualizado_en
FROM configuracion_sistema
WHERE categoria = 'AI'
ORDER BY clave;

-- ============================================================================
-- SECCIÓN 2: RESUMEN DE CONFIGURACIÓN
-- ============================================================================
SELECT 
    '=== RESUMEN DE CONFIGURACIÓN ===' AS tipo,
    COUNT(*) AS total_configuraciones,
    SUM(CASE WHEN clave = 'openai_api_key' AND valor IS NOT NULL AND valor != '' AND valor LIKE 'sk-%' THEN 1 ELSE 0 END) AS api_key_configurada,
    SUM(CASE WHEN clave = 'activo' AND valor = 'true' THEN 1 ELSE 0 END) AS ai_activo,
    SUM(CASE WHEN clave = 'modelo' THEN 1 ELSE 0 END) AS modelo_configurado,
    SUM(CASE WHEN clave = 'temperatura' THEN 1 ELSE 0 END) AS temperatura_configurada,
    SUM(CASE WHEN clave = 'max_tokens' THEN 1 ELSE 0 END) AS max_tokens_configurado,
    SUM(CASE WHEN clave = 'modelo_fine_tuned' AND valor IS NOT NULL AND valor != '' THEN 1 ELSE 0 END) AS modelo_fine_tuned_configurado,
    SUM(CASE WHEN clave = 'system_prompt_personalizado' AND valor IS NOT NULL AND valor != '' THEN 1 ELSE 0 END) AS prompt_personalizado_configurado
FROM configuracion_sistema
WHERE categoria = 'AI';

-- ============================================================================
-- SECCIÓN 3: DOCUMENTOS AI (solo si la tabla existe)
-- ============================================================================
-- NOTA: Esta sección solo funciona si la tabla documentos_ai existe
-- Si obtienes error "relation does not exist", omite esta sección
-- Para crear la tabla, ejecuta: alembic upgrade head
-- ============================================================================
-- Si la tabla no existe, esta consulta fallará - omite esta sección
SELECT 
    '=== DOCUMENTOS AI ===' AS seccion,
    id,
    titulo,
    descripcion,
    nombre_archivo,
    tipo_archivo,
    tamaño_bytes,
    CASE 
        WHEN tamaño_bytes IS NULL THEN 'N/A'
        WHEN tamaño_bytes < 1024 THEN tamaño_bytes || ' B'
        WHEN tamaño_bytes < 1024 * 1024 THEN ROUND(tamaño_bytes::numeric / 1024, 2) || ' KB'
        ELSE ROUND(tamaño_bytes::numeric / (1024 * 1024), 2) || ' MB'
    END AS tamaño_formateado,
    contenido_procesado,
    activo,
    CASE 
        WHEN contenido_procesado = TRUE AND activo = TRUE THEN '✅ Activo y procesado'
        WHEN contenido_procesado = TRUE AND activo = FALSE THEN '⚠️ Procesado pero inactivo'
        WHEN contenido_procesado = FALSE AND activo = TRUE THEN '⚠️ Activo pero NO procesado'
        ELSE '❌ Inactivo y no procesado'
    END AS estado,
    CASE 
        WHEN contenido_texto IS NULL OR contenido_texto = '' THEN '❌ Sin contenido'
        ELSE '✅ Con contenido (' || LENGTH(contenido_texto) || ' caracteres)'
    END AS contenido_texto_estado,
    creado_en,
    actualizado_en
FROM documentos_ai
ORDER BY creado_en DESC;

-- ============================================================================
-- SECCIÓN 4: RESUMEN DE DOCUMENTOS
-- ============================================================================
SELECT 
    '=== RESUMEN DOCUMENTOS AI ===' AS tipo,
    COUNT(*) AS total_documentos,
    SUM(CASE WHEN activo = TRUE THEN 1 ELSE 0 END) AS documentos_activos,
    SUM(CASE WHEN contenido_procesado = TRUE THEN 1 ELSE 0 END) AS documentos_procesados,
    SUM(CASE WHEN activo = TRUE AND contenido_procesado = TRUE THEN 1 ELSE 0 END) AS documentos_listos,
    SUM(CASE WHEN activo = TRUE AND contenido_procesado = FALSE THEN 1 ELSE 0 END) AS documentos_activos_sin_procesar,
    SUM(CASE WHEN contenido_texto IS NOT NULL AND contenido_texto != '' THEN 1 ELSE 0 END) AS documentos_con_contenido,
    SUM(tamaño_bytes) AS tamaño_total_bytes,
    CASE 
        WHEN SUM(tamaño_bytes) IS NULL THEN 'N/A'
        WHEN SUM(tamaño_bytes) < 1024 * 1024 THEN ROUND(SUM(tamaño_bytes)::numeric / 1024, 2) || ' KB'
        ELSE ROUND(SUM(tamaño_bytes)::numeric / (1024 * 1024), 2) || ' MB'
    END AS tamaño_total_formateado
FROM documentos_ai;

-- ============================================================================
-- SECCIÓN 5: VARIABLES DE PROMPT (OPCIONAL - solo si la tabla existe)
-- ============================================================================
-- ⚠️ IMPORTANTE: Esta sección requiere que la tabla ai_prompt_variables exista
-- Si obtienes error "relation ai_prompt_variables does not exist":
--   1. OMITE esta sección (comenta o no ejecutes estas líneas)
--   2. O ejecuta la migración: alembic upgrade head
-- ============================================================================
-- Para verificar si la tabla existe, ejecuta primero la verificación de tablas
-- Si la tabla NO existe, COMENTA o NO EJECUTES las siguientes 2 consultas
-- ============================================================================

-- CONSULTA 5A: Listar variables de prompt
-- ⚠️ COMENTAR si la tabla no existe
/*
SELECT 
    '=== VARIABLES DE PROMPT ===' AS seccion,
    id,
    variable,
    descripcion,
    activo,
    orden,
    CASE 
        WHEN activo = TRUE THEN '✅ Activa'
        ELSE '❌ Inactiva'
    END AS estado,
    creado_en,
    actualizado_en
FROM ai_prompt_variables
ORDER BY orden, variable;
*/

-- CONSULTA 5B: Resumen de variables
-- ⚠️ COMENTAR si la tabla no existe
/*
SELECT 
    '=== RESUMEN VARIABLES PROMPT ===' AS tipo,
    COUNT(*) AS total_variables,
    SUM(CASE WHEN activo = TRUE THEN 1 ELSE 0 END) AS variables_activas,
    SUM(CASE WHEN activo = FALSE THEN 1 ELSE 0 END) AS variables_inactivas
FROM ai_prompt_variables;
*/

-- ============================================================================
-- SECCIÓN 7: EMBEDDINGS (solo si la tabla existe)
-- ============================================================================
-- NOTA: Esta sección solo funciona si las tablas documento_ai_embeddings y documentos_ai existen
-- Si obtienes error "relation does not exist", omite esta sección
-- Para crear las tablas, ejecuta: alembic upgrade head
-- ============================================================================
-- Si las tablas no existen, esta consulta fallará - omite esta sección
SELECT 
    '=== EMBEDDINGS DE DOCUMENTOS (RAG) ===' AS seccion,
    de.id,
    de.documento_id,
    da.titulo AS documento_titulo,
    de.chunk_index,
    LENGTH(de.texto_chunk) AS caracteres_chunk,
    CASE 
        WHEN de.embedding IS NULL THEN '❌ Sin embedding'
        WHEN jsonb_array_length(de.embedding::jsonb) = 0 THEN '⚠️ Embedding vacío'
        ELSE '✅ Embedding (' || jsonb_array_length(de.embedding::jsonb) || ' dimensiones)'
    END AS estado_embedding,
    de.creado_en
FROM documento_ai_embeddings de
LEFT JOIN documentos_ai da ON de.documento_id = da.id
ORDER BY de.documento_id, de.chunk_index;

-- ============================================================================
-- SECCIÓN 8: RESUMEN DE EMBEDDINGS
-- ============================================================================
SELECT 
    '=== RESUMEN EMBEDDINGS ===' AS tipo,
    COUNT(*) AS total_embeddings,
    COUNT(DISTINCT documento_id) AS documentos_con_embeddings,
    SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) AS embeddings_con_datos,
    AVG(CASE 
        WHEN embedding IS NOT NULL THEN jsonb_array_length(embedding::jsonb)
        ELSE NULL
    END) AS dimensiones_promedio,
    SUM(LENGTH(texto_chunk)) AS total_caracteres_chunks
FROM documento_ai_embeddings;

-- ============================================================================
-- SECCIÓN 9: VERIFICACIÓN DE INTEGRIDAD
-- ============================================================================
SELECT 
    '=== VERIFICACIÓN DE INTEGRIDAD ===' AS tipo,
    'Configuración AI' AS item,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'openai_api_key' 
            AND valor IS NOT NULL 
            AND valor != '' 
            AND valor LIKE 'sk-%'
        ) THEN '✅ API Key configurada'
        ELSE '❌ API Key NO configurada o inválida'
    END AS estado

UNION ALL

SELECT 
    'Verificación',
    'AI Activo',
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'activo' 
            AND valor = 'true'
        ) THEN '✅ AI está activo'
        ELSE '⚠️ AI está inactivo'
    END

UNION ALL

SELECT 
    'Verificación',
    'Documentos Activos',
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'documentos_ai'
        ) THEN '⚠️ Tabla no existe (ejecutar migración)'
        WHEN EXISTS (
            SELECT 1 FROM documentos_ai 
            WHERE activo = TRUE 
            AND contenido_procesado = TRUE
        ) THEN '✅ Hay documentos activos y procesados'
        WHEN EXISTS (
            SELECT 1 FROM documentos_ai 
            WHERE activo = TRUE 
            AND contenido_procesado = FALSE
        ) THEN '⚠️ Hay documentos activos pero NO procesados'
        ELSE '❌ No hay documentos activos'
    END

UNION ALL

SELECT 
    'Verificación',
    'Embeddings Disponibles',
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'documento_ai_embeddings'
        ) THEN '⚠️ Tabla no existe (opcional - para RAG)'
        WHEN EXISTS (
            SELECT 1 FROM documento_ai_embeddings 
            WHERE embedding IS NOT NULL
        ) THEN '✅ Hay embeddings disponibles para RAG'
        ELSE '⚠️ No hay embeddings disponibles'
    END

UNION ALL

SELECT 
    'Verificación',
    'Variables de Prompt',
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'ai_prompt_variables'
        ) THEN '⚠️ Tabla no existe (opcional)'
        WHEN EXISTS (
            SELECT 1 FROM ai_prompt_variables 
            WHERE activo = TRUE
        ) THEN '✅ Hay variables de prompt activas'
        ELSE 'ℹ️ No hay variables de prompt personalizadas'
    END;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

