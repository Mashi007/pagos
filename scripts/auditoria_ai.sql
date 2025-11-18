-- ============================================================================
-- SCRIPT DE AUDITORÍA INTEGRAL DE CONFIGURACIÓN AI
-- Para ejecutar en DBeaver
-- ============================================================================
-- Este script audita toda la configuración relacionada con AI:
-- 1. Configuraciones de AI en configuracion_sistema
-- 2. Documentos AI cargados (tabla: documentos_ai)
-- 3. Variables de prompt personalizadas (tabla: ai_prompt_variables)
-- 4. Embeddings de documentos (RAG) (tabla: documento_ai_embeddings)
-- 5. Conversaciones de AI (si existe)
-- ============================================================================
-- NOTA: Si alguna tabla no existe, esa sección retornará 0 filas
-- IMPORTANTE: Si obtienes error "relation does not exist", ejecuta las secciones
-- por separado o usa el archivo: auditoria_ai_por_secciones.sql
-- ============================================================================
-- NOMBRES CORRECTOS DE TABLAS:
-- - documentos_ai (NO documento_ai)
-- - documento_ai_embeddings (NO documento_embedding)
-- - ai_prompt_variables (NO ai_prompt_variable)
-- ============================================================================

-- Verificar existencia de tablas (opcional - solo informativo)
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
-- 1. CONFIGURACIÓN DE AI EN configuracion_sistema
-- ============================================================================
SELECT 
    '=== CONFIGURACIÓN DE AI ===' AS seccion,
    NULL AS id,
    NULL AS categoria,
    NULL AS clave,
    NULL AS valor,
    NULL AS tipo_dato,
    NULL AS activo,
    NULL AS creado_en,
    NULL AS actualizado_en
WHERE FALSE

UNION ALL

SELECT 
    'Configuración AI' AS seccion,
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
-- 2. RESUMEN DE CONFIGURACIÓN DE AI
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
-- 3. VALORES ESPECÍFICOS DE CONFIGURACIÓN
-- ============================================================================
SELECT 
    '=== VALORES DE CONFIGURACIÓN ===' AS tipo,
    clave,
    CASE 
        WHEN clave = 'openai_api_key' THEN 
            CASE 
                WHEN valor IS NULL OR valor = '' THEN '❌ NO CONFIGURADO'
                WHEN valor NOT LIKE 'sk-%' THEN '⚠️ FORMATO INCORRECTO'
                ELSE '✅ Configurado (' || LENGTH(valor) || ' caracteres)'
            END
        ELSE COALESCE(valor, 'NULL')
    END AS valor_mostrado,
    tipo_dato,
    requerido,
    visible_frontend,
    creado_en,
    actualizado_en
FROM configuracion_sistema
WHERE categoria = 'AI'
ORDER BY 
    CASE clave
        WHEN 'openai_api_key' THEN 1
        WHEN 'activo' THEN 2
        WHEN 'modelo' THEN 3
        WHEN 'modelo_fine_tuned' THEN 4
        WHEN 'temperatura' THEN 5
        WHEN 'max_tokens' THEN 6
        WHEN 'system_prompt_personalizado' THEN 7
        ELSE 8
    END;

-- ============================================================================
-- 4. DOCUMENTOS AI CARGADOS
-- ============================================================================
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
-- 5. RESUMEN DE DOCUMENTOS AI
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
-- 6. VARIABLES DE PROMPT PERSONALIZADAS
-- ============================================================================
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

-- ============================================================================
-- 7. RESUMEN DE VARIABLES DE PROMPT
-- ============================================================================
SELECT 
    '=== RESUMEN VARIABLES PROMPT ===' AS tipo,
    COUNT(*) AS total_variables,
    SUM(CASE WHEN activo = TRUE THEN 1 ELSE 0 END) AS variables_activas,
    SUM(CASE WHEN activo = FALSE THEN 1 ELSE 0 END) AS variables_inactivas
FROM ai_prompt_variables;

-- ============================================================================
-- 8. EMBEDDINGS DE DOCUMENTOS (RAG)
-- ============================================================================
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
-- 9. RESUMEN DE EMBEDDINGS
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
-- 10. EMBEDDINGS POR DOCUMENTO
-- ============================================================================
SELECT 
    '=== EMBEDDINGS POR DOCUMENTO ===' AS tipo,
    da.id AS documento_id,
    da.titulo,
    da.activo AS documento_activo,
    COUNT(de.id) AS total_embeddings,
    SUM(CASE WHEN de.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embeddings_validos,
    SUM(LENGTH(de.texto_chunk)) AS total_caracteres,
    CASE 
        WHEN COUNT(de.id) = 0 THEN '❌ Sin embeddings'
        WHEN COUNT(de.id) > 0 AND SUM(CASE WHEN de.embedding IS NOT NULL THEN 1 ELSE 0 END) = COUNT(de.id) THEN '✅ Todos los embeddings válidos'
        ELSE '⚠️ Algunos embeddings inválidos'
    END AS estado
FROM documentos_ai da
LEFT JOIN documento_ai_embeddings de ON da.id = de.documento_id
GROUP BY da.id, da.titulo, da.activo
ORDER BY total_embeddings DESC;

-- ============================================================================
-- 11. VERIFICACIÓN DE INTEGRIDAD
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
        WHEN EXISTS (
            SELECT 1 FROM ai_prompt_variables 
            WHERE activo = TRUE
        ) THEN '✅ Hay variables de prompt activas'
        ELSE 'ℹ️ No hay variables de prompt personalizadas'
    END;

-- ============================================================================
-- 12. ESTADÍSTICAS GENERALES
-- ============================================================================
SELECT 
    '=== ESTADÍSTICAS GENERALES ===' AS tipo,
    (SELECT COUNT(*) FROM configuracion_sistema WHERE categoria = 'AI') AS configuraciones_ai,
    (SELECT COUNT(*) FROM documentos_ai) AS total_documentos,
    (SELECT COUNT(*) FROM documentos_ai WHERE activo = TRUE) AS documentos_activos,
    (SELECT COUNT(*) FROM ai_prompt_variables) AS total_variables_prompt,
    (SELECT COUNT(*) FROM ai_prompt_variables WHERE activo = TRUE) AS variables_activas,
    (SELECT COUNT(*) FROM documento_ai_embeddings) AS total_embeddings,
    (SELECT COUNT(DISTINCT documento_id) FROM documento_ai_embeddings) AS documentos_con_embeddings;

-- ============================================================================
-- 13. ANÁLISIS DE SEGURIDAD
-- ============================================================================
SELECT 
    '=== ANÁLISIS DE SEGURIDAD ===' AS tipo,
    'API Key Configurada' AS item,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'openai_api_key' 
            AND valor IS NOT NULL 
            AND valor != '' 
            AND LENGTH(valor) >= 20
        ) THEN '✅ API Key configurada'
        ELSE '❌ API Key NO configurada o inválida'
    END AS estado,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'openai_api_key' 
            AND valor LIKE 'sk-%'
        ) THEN '✅ Formato correcto (sk-...)'
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'openai_api_key' 
            AND valor IS NOT NULL
        ) THEN '⚠️ Formato incorrecto (no empieza con sk-)'
        ELSE '❌ No configurada'
    END AS formato

UNION ALL

SELECT 
    'Seguridad',
    'API Key Encriptada',
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'openai_api_key' 
            AND valor LIKE 'gAAAAAB%'  -- Formato típico de Fernet
        ) THEN '✅ API Key parece encriptada'
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'openai_api_key' 
            AND valor IS NOT NULL
        ) THEN '⚠️ API Key NO encriptada (texto plano)'
        ELSE 'N/A'
    END,
    '🔴 CRÍTICO: API Key debe estar encriptada en producción'

UNION ALL

SELECT 
    'Seguridad',
    'Control de Acceso',
    '✅ Verificar en código: Solo admins pueden acceder',
    'Revisar: is_admin check en endpoints'

UNION ALL

SELECT 
    'Seguridad',
    'Rate Limiting',
    '⚠️ Verificar en código: Rate limiting implementado',
    'Revisar: @limiter.limit() en endpoints';

-- ============================================================================
-- 14. ANÁLISIS DE PERFORMANCE
-- ============================================================================
SELECT 
    '=== ANÁLISIS DE PERFORMANCE ===' AS tipo,
    'Índices en configuracion_sistema' AS item,
    COUNT(*) AS total_indices,
    string_agg(indexname, ', ') AS indices
FROM pg_indexes
WHERE tablename = 'configuracion_sistema'
    AND schemaname = 'public'

UNION ALL

SELECT 
    'Performance',
    'Índices en documentos_ai',
    COUNT(*),
    string_agg(indexname, ', ')
FROM pg_indexes
WHERE tablename = 'documentos_ai'
    AND schemaname = 'public'

UNION ALL

SELECT 
    'Performance',
    'Índices en documento_ai_embeddings',
    COUNT(*),
    string_agg(indexname, ', ')
FROM pg_indexes
WHERE tablename = 'documento_ai_embeddings'
    AND schemaname = 'public'

UNION ALL

SELECT 
    'Performance',
    'Índices en ai_prompt_variables',
    COUNT(*),
    string_agg(indexname, ', ')
FROM pg_indexes
WHERE tablename = 'ai_prompt_variables'
    AND schemaname = 'public';

-- ============================================================================
-- 15. RECOMENDACIONES ESPECÍFICAS
-- ============================================================================
SELECT 
    '=== RECOMENDACIONES ===' AS tipo,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'openai_api_key' 
            AND valor LIKE 'gAAAAAB%'
        ) AND EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'openai_api_key' 
            AND valor IS NOT NULL
        ) THEN '🔴 CRÍTICO: Encriptar API Key de OpenAI'
        WHEN NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'configuracion_sistema' 
            AND indexname LIKE '%categoria%'
        ) THEN '🟡 MEDIO: Agregar índice en configuracion_sistema(categoria, clave)'
        WHEN NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'documentos_ai' 
            AND indexname LIKE '%activo%'
        ) THEN '🟡 MEDIO: Agregar índice en documentos_ai(activo, contenido_procesado)'
        WHEN EXISTS (
            SELECT 1 FROM documento_ai_embeddings de
            LEFT JOIN documentos_ai da ON de.documento_id = da.id
            WHERE da.id IS NULL
        ) THEN '🟡 MEDIO: Hay embeddings huérfanos (documento eliminado)'
        ELSE '✅ Sin recomendaciones críticas'
    END AS recomendacion,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'openai_api_key' 
            AND valor LIKE 'gAAAAAB%'
        ) AND EXISTS (
            SELECT 1 FROM configuracion_sistema 
            WHERE categoria = 'AI' 
            AND clave = 'openai_api_key' 
            AND valor IS NOT NULL
        ) THEN 'Prioridad: ALTA - Implementar encriptación con cryptography.fernet'
        WHEN NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'configuracion_sistema' 
            AND indexname LIKE '%categoria%'
        ) THEN 'Prioridad: MEDIA - Mejora performance de consultas'
        WHEN NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'documentos_ai' 
            AND indexname LIKE '%activo%'
        ) THEN 'Prioridad: MEDIA - Mejora performance de filtros'
        WHEN EXISTS (
            SELECT 1 FROM documento_ai_embeddings de
            LEFT JOIN documentos_ai da ON de.documento_id = da.id
            WHERE da.id IS NULL
        ) THEN 'Prioridad: MEDIA - Limpiar datos huérfanos o agregar CASCADE DELETE'
        ELSE 'Sistema en buen estado'
    END AS detalle;

-- ============================================================================
-- 16. EMBEDDINGS HUÉRFANOS (si existen)
-- ============================================================================
SELECT 
    '=== EMBEDDINGS HUÉRFANOS ===' AS tipo,
    de.id AS embedding_id,
    de.documento_id,
    '❌ Documento no existe' AS estado,
    de.creado_en
FROM documento_ai_embeddings de
LEFT JOIN documentos_ai da ON de.documento_id = da.id
WHERE da.id IS NULL
ORDER BY de.creado_en DESC;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Para ejecutar todo el script:
-- 1. Selecciona todo el contenido (Ctrl+A)
-- 2. Ejecuta (Ctrl+Enter o F5)
-- 3. Revisa cada sección en los resultados
-- 
-- NOTAS:
-- - Algunas consultas pueden retornar 0 filas si no hay datos
-- - Revisa especialmente las secciones de Seguridad y Recomendaciones
-- - Los embeddings huérfanos indican posibles problemas de integridad
-- ============================================================================

