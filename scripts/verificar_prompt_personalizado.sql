-- ============================================================================
-- VERIFICACIÓN DE PROMPT PERSONALIZADO DE AI
-- ============================================================================
-- Este script verifica si hay un prompt personalizado configurado
-- y si está siendo usado por el sistema
-- 
-- NOTA: La tabla ai_prompt_variables es OPCIONAL
-- Si no existe, el script funcionará igual (solo omitirá esa sección)
-- ============================================================================

-- 1. VERIFICAR SI EXISTE PROMPT PERSONALIZADO
-- ============================================================================
SELECT 
    '=== PROMPT PERSONALIZADO ===' AS tipo,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema
            WHERE categoria = 'AI'
            AND clave = 'system_prompt_personalizado'
            AND valor IS NOT NULL
            AND valor != ''
            AND LENGTH(TRIM(valor)) > 0
        ) THEN '✅ PROMPT PERSONALIZADO CONFIGURADO'
        ELSE '❌ NO HAY PROMPT PERSONALIZADO (usando default)'
    END AS estado;

-- 2. VER DETALLES DEL PROMPT PERSONALIZADO
-- ============================================================================
SELECT 
    '=== DETALLES DEL PROMPT ===' AS seccion,
    id,
    categoria,
    clave,
    CASE 
        WHEN LENGTH(valor) > 100 THEN LEFT(valor, 100) || '... (truncado)'
        ELSE valor
    END AS valor_preview,
    LENGTH(valor) AS longitud_caracteres,
    tipo_dato,
    descripcion,
    visible_frontend,
    solo_lectura,
    creado_en,
    actualizado_en
FROM configuracion_sistema
WHERE categoria = 'AI'
AND clave = 'system_prompt_personalizado';

-- 3. VERIFICAR PLACEHOLDERS REQUERIDOS
-- ============================================================================
SELECT 
    '=== VERIFICACIÓN DE PLACEHOLDERS ===' AS tipo,
    'Placeholder' AS item,
    CASE 
        WHEN valor LIKE '%{resumen_bd}%' THEN '✅ Presente'
        ELSE '❌ FALTANTE'
    END AS resumen_bd,
    CASE 
        WHEN valor LIKE '%{info_cliente_buscado}%' THEN '✅ Presente'
        ELSE '❌ FALTANTE'
    END AS info_cliente_buscado,
    CASE 
        WHEN valor LIKE '%{datos_adicionales}%' THEN '✅ Presente'
        ELSE '❌ FALTANTE'
    END AS datos_adicionales,
    CASE 
        WHEN valor LIKE '%{info_esquema}%' THEN '✅ Presente'
        ELSE '❌ FALTANTE'
    END AS info_esquema,
    CASE 
        WHEN valor LIKE '%{contexto_documentos}%' THEN '✅ Presente'
        ELSE '❌ FALTANTE'
    END AS contexto_documentos
FROM configuracion_sistema
WHERE categoria = 'AI'
AND clave = 'system_prompt_personalizado'
AND valor IS NOT NULL
AND valor != '';

-- 4. RESUMEN DE CONFIGURACIÓN
-- ============================================================================
SELECT 
    '=== RESUMEN ===' AS tipo,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema
            WHERE categoria = 'AI'
            AND clave = 'system_prompt_personalizado'
            AND valor IS NOT NULL
            AND valor != ''
        ) THEN '✅ Usando Prompt Personalizado'
        ELSE 'ℹ️ Usando Prompt Default'
    END AS prompt_activo,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema
            WHERE categoria = 'AI'
            AND clave = 'system_prompt_personalizado'
            AND valor IS NOT NULL
            AND valor != ''
            AND valor LIKE '%{resumen_bd}%'
            AND valor LIKE '%{info_cliente_buscado}%'
            AND valor LIKE '%{datos_adicionales}%'
            AND valor LIKE '%{info_esquema}%'
            AND valor LIKE '%{contexto_documentos}%'
        ) THEN '✅ Todos los placeholders presentes'
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema
            WHERE categoria = 'AI'
            AND clave = 'system_prompt_personalizado'
            AND valor IS NOT NULL
            AND valor != ''
        ) THEN '⚠️ Algunos placeholders faltantes'
        ELSE 'N/A'
    END AS validacion_placeholders;

-- 5. VER VARIABLES PERSONALIZADAS (si existen)
-- ============================================================================
-- NOTA: Esta sección solo se ejecuta si la tabla ai_prompt_variables existe
-- Si la tabla no existe, comenta esta sección o ignora el error

-- Verificar si la tabla existe antes de consultar
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'ai_prompt_variables'
    ) THEN
        -- La tabla existe, se puede consultar
        RAISE NOTICE 'Tabla ai_prompt_variables existe';
    ELSE
        RAISE NOTICE 'Tabla ai_prompt_variables NO existe - omitiendo sección de variables';
    END IF;
END $$;

-- Si la tabla existe, ejecutar estas consultas:
-- (Descomenta si la tabla existe)

/*
SELECT 
    '=== VARIABLES PERSONALIZADAS ===' AS seccion,
    id,
    variable,
    descripcion,
    CASE 
        WHEN activo = TRUE THEN '✅ Activa'
        ELSE '❌ Inactiva'
    END AS estado,
    orden,
    creado_en,
    actualizado_en
FROM ai_prompt_variables
WHERE activo = TRUE
ORDER BY orden, variable;

-- 6. CONTAR VARIABLES PERSONALIZADAS
-- ============================================================================
SELECT 
    '=== RESUMEN VARIABLES ===' AS tipo,
    COUNT(*) AS total_variables,
    SUM(CASE WHEN activo = TRUE THEN 1 ELSE 0 END) AS variables_activas,
    SUM(CASE WHEN activo = FALSE THEN 1 ELSE 0 END) AS variables_inactivas
FROM ai_prompt_variables;
*/

-- Alternativa: Consulta condicional (solo funciona si la tabla existe)
SELECT 
    '=== VARIABLES PERSONALIZADAS ===' AS tipo,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'ai_prompt_variables'
        ) THEN '✅ Tabla existe (ver detalles descomentando sección anterior)'
        ELSE 'ℹ️ Tabla ai_prompt_variables NO existe (opcional, no afecta el prompt)'
    END AS estado;

-- ============================================================================
-- NOTAS:
-- ============================================================================
-- 1. Si "PROMPT PERSONALIZADO CONFIGURADO" = ✅, el sistema lo está usando
-- 2. Si todos los placeholders están presentes, el prompt es válido
-- 3. El sistema verifica automáticamente en AIChatService.construir_system_prompt()
-- 4. Los logs del backend mostrarán "Usando prompt personalizado" cuando esté activo
-- ============================================================================

