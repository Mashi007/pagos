-- ============================================================
-- CONSULTA: PORCENTAJE DE PRÉSTAMOS CON ESTADO APROBADO
-- ============================================================
-- Esta consulta calcula qué porcentaje de los préstamos
-- tienen el estado 'APROBADO'
-- ============================================================

-- ============================================================
-- CONSULTA PRINCIPAL: PORCENTAJE DE PRÉSTAMOS APROBADOS
-- ============================================================

SELECT 
    -- Total de préstamos
    COUNT(*) AS total_prestamos,
    
    -- Préstamos aprobados
    COUNT(*) FILTER (WHERE estado = 'APROBADO') AS prestamos_aprobados,
    
    -- Préstamos NO aprobados (otros estados)
    COUNT(*) FILTER (WHERE estado != 'APROBADO') AS prestamos_no_aprobados,
    
    -- Porcentaje de préstamos aprobados
    ROUND(
        (COUNT(*) FILTER (WHERE estado = 'APROBADO')::numeric / 
         NULLIF(COUNT(*), 0)) * 100, 
        2
    ) AS porcentaje_aprobados,
    
    -- Porcentaje de préstamos NO aprobados
    ROUND(
        (COUNT(*) FILTER (WHERE estado != 'APROBADO')::numeric / 
         NULLIF(COUNT(*), 0)) * 100, 
        2
    ) AS porcentaje_no_aprobados

FROM prestamos;

-- ============================================================
-- CONSULTA DETALLADA: DISTRIBUCIÓN POR ESTADO
-- ============================================================
-- Muestra el desglose de préstamos por cada estado

SELECT 
    estado,
    COUNT(*) AS cantidad,
    ROUND(
        (COUNT(*)::numeric / 
         NULLIF((SELECT COUNT(*) FROM prestamos), 0)) * 100, 
        2
    ) AS porcentaje
FROM prestamos
GROUP BY estado
ORDER BY cantidad DESC;

-- ============================================================
-- CONSULTA SIMPLIFICADA: SOLO EL PORCENTAJE APROBADO
-- ============================================================

SELECT 
    ROUND(
        (COUNT(*) FILTER (WHERE estado = 'APROBADO')::numeric / 
         NULLIF(COUNT(*), 0)) * 100, 
        2
    ) AS porcentaje_prestamos_aprobados
FROM prestamos;

-- ============================================================
-- CONSULTA CON DESGLOSE ADICIONAL: POR FECHA DE REGISTRO
-- ============================================================
-- Muestra el porcentaje de aprobados agrupado por mes/año

SELECT 
    TO_CHAR(fecha_registro, 'YYYY-MM') AS mes_año,
    COUNT(*) AS total_prestamos,
    COUNT(*) FILTER (WHERE estado = 'APROBADO') AS prestamos_aprobados,
    ROUND(
        (COUNT(*) FILTER (WHERE estado = 'APROBADO')::numeric / 
         NULLIF(COUNT(*), 0)) * 100, 
        2
    ) AS porcentaje_aprobados
FROM prestamos
GROUP BY TO_CHAR(fecha_registro, 'YYYY-MM')
ORDER BY mes_año DESC
LIMIT 12;

-- ============================================================
-- NOTAS IMPORTANTES:
-- ============================================================
-- 1. TABLA: prestamos (plural)
-- 2. COLUMNA DE ESTADO: estado
-- 3. ESTADO APROBADO: 'APROBADO' (mayúsculas)
-- 4. OTROS ESTADOS POSIBLES: 'DRAFT', 'EN_REVISION', 'RECHAZADO', 'FINALIZADO'
-- 5. El cálculo usa FILTER para contar solo los aprobados
-- 6. NULLIF evita división por cero
-- ============================================================

