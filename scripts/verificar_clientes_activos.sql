-- ============================================================================
-- SCRIPT PARA VERIFICAR QUE TODOS LOS CLIENTES ACTIVOS TIENEN activo = true
-- ============================================================================
-- Este script verifica la consistencia entre los campos 'estado' y 'activo'
-- de la tabla clientes. Todos los clientes con estado='ACTIVO' deben tener
-- activo=true según las reglas del sistema.
-- ============================================================================

-- 1. RESUMEN GENERAL DE CLIENTES POR ESTADO Y ACTIVO
-- ============================================================================
SELECT 
    'RESUMEN GENERAL' AS tipo_consulta,
    estado,
    activo,
    COUNT(*) AS cantidad_clientes
FROM clientes
GROUP BY estado, activo
ORDER BY estado, activo;

-- 2. VERIFICACIÓN: CLIENTES CON estado='ACTIVO' Y activo=false (INCONSISTENCIA)
-- ============================================================================
SELECT 
    'INCONSISTENCIAS ENCONTRADAS' AS tipo_consulta,
    id,
    cedula,
    nombres,
    estado,
    activo,
    fecha_registro,
    fecha_actualizacion,
    usuario_registro
FROM clientes
WHERE estado = 'ACTIVO' AND activo = false
ORDER BY id;

-- 3. VERIFICACIÓN: CLIENTES CON estado='ACTIVO' Y activo=true (CORRECTO)
-- ============================================================================
SELECT 
    'CLIENTES ACTIVOS CORRECTOS' AS tipo_consulta,
    COUNT(*) AS total_clientes_activos_correctos
FROM clientes
WHERE estado = 'ACTIVO' AND activo = true;

-- 4. VERIFICACIÓN: CLIENTES CON estado INACTIVO/FINALIZADO Y activo=true (INCONSISTENCIA)
-- ============================================================================
SELECT 
    'INCONSISTENCIAS: INACTIVO/FINALIZADO CON activo=true' AS tipo_consulta,
    id,
    cedula,
    nombres,
    estado,
    activo,
    fecha_registro,
    fecha_actualizacion,
    usuario_registro
FROM clientes
WHERE estado IN ('INACTIVO', 'FINALIZADO') AND activo = true
ORDER BY estado, id;

-- 5. RESUMEN DE VERIFICACIÓN FINAL
-- ============================================================================
SELECT 
    'RESUMEN DE VERIFICACIÓN' AS tipo_consulta,
    (SELECT COUNT(*) FROM clientes WHERE estado = 'ACTIVO' AND activo = true) AS activos_correctos,
    (SELECT COUNT(*) FROM clientes WHERE estado = 'ACTIVO' AND activo = false) AS activos_incorrectos,
    (SELECT COUNT(*) FROM clientes WHERE estado IN ('INACTIVO', 'FINALIZADO') AND activo = true) AS inactivos_incorrectos,
    (SELECT COUNT(*) FROM clientes WHERE estado = 'ACTIVO') AS total_estado_activo,
    CASE 
        WHEN (SELECT COUNT(*) FROM clientes WHERE estado = 'ACTIVO' AND activo = false) = 0 
             AND (SELECT COUNT(*) FROM clientes WHERE estado IN ('INACTIVO', 'FINALIZADO') AND activo = true) = 0
        THEN '✅ TODOS LOS CLIENTES ESTÁN CORRECTOS'
        ELSE '⚠️ SE ENCONTRARON INCONSISTENCIAS'
    END AS resultado_verificacion;

-- ============================================================================
-- NOTA: Si se encuentran inconsistencias, ejecuta el siguiente script
-- para corregirlas automáticamente:
-- ============================================================================
-- 
-- -- CORRECCIÓN AUTOMÁTICA (descomentar para ejecutar):
-- 
-- -- Corregir clientes con estado='ACTIVO' pero activo=false
-- UPDATE clientes 
-- SET activo = true, 
--     fecha_actualizacion = CURRENT_TIMESTAMP
-- WHERE estado = 'ACTIVO' AND activo = false;
-- 
-- -- Corregir clientes con estado INACTIVO/FINALIZADO pero activo=true
-- UPDATE clientes 
-- SET activo = false, 
--     fecha_actualizacion = CURRENT_TIMESTAMP
-- WHERE estado IN ('INACTIVO', 'FINALIZADO') AND activo = true;
-- 
-- ============================================================================

