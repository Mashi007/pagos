-- ============================================================
-- CÓDIGO SQL PARA DBEAVER - GRÁFICO "FINANCIAMIENTO APROBADO POR MES"
-- ============================================================
-- Este gráfico muestra la tendencia mensual de nuevos financiamientos
-- aprobados basado en la fecha de registro del préstamo.
-- ============================================================

-- ============================================================
-- 1. VERIFICAR TODAS LAS COLUMNAS DE LA TABLA prestamos
-- ============================================================
-- Muestra TODAS las columnas disponibles en la tabla prestamos

SELECT 
    column_name AS "Nombre Columna",
    data_type AS "Tipo de Dato",
    character_maximum_length AS "Longitud Máx",
    is_nullable AS "Permite NULL",
    column_default AS "Valor por Defecto",
    ordinal_position AS "Posición"
FROM 
    information_schema.columns
WHERE 
    table_schema = 'public'
    AND table_name = 'prestamos'
ORDER BY 
    ordinal_position;

-- ============================================================
-- 1B. VERIFICAR SOLO COLUMNAS CLAVE PARA EL GRÁFICO
-- ============================================================
-- Columnas específicas usadas por el gráfico "Financiamiento Aprobado por Mes"

SELECT 
    column_name AS "Nombre Columna",
    data_type AS "Tipo de Dato",
    is_nullable AS "Permite NULL"
FROM 
    information_schema.columns
WHERE 
    table_schema = 'public'
    AND table_name = 'prestamos'
    AND column_name IN (
        'id',
        'fecha_registro',        -- ⭐ FECHA usada para agrupar por mes
        'total_financiamiento',   -- ⭐ MONTO que se suma
        'estado',                 -- ⭐ FILTRO: solo 'APROBADO'
        'analista',               -- Filtro opcional
        'producto_financiero',    -- Filtro opcional (analista alternativo)
        'concesionario',          -- Filtro opcional
        'producto',               -- Filtro opcional (modelo)
        'modelo_vehiculo'         -- Filtro opcional (modelo alternativo)
    )
ORDER BY 
    ordinal_position;

-- ============================================================
-- 2. VERIFICAR VALORES DE ESTADO DISPONIBLES
-- ============================================================
-- Verifica qué valores tiene la columna 'estado' en la tabla

SELECT 
    estado AS "Estado",
    COUNT(*) AS "Cantidad de Préstamos",
    SUM(total_financiamiento) AS "Total Financiamiento",
    ROUND(AVG(total_financiamiento), 2) AS "Promedio por Préstamo"
FROM 
    prestamos
GROUP BY 
    estado
ORDER BY 
    COUNT(*) DESC;

-- ============================================================
-- 3. CONSULTA EXACTA QUE USA EL BACKEND
-- ============================================================
-- Esta es la consulta SQL equivalente a lo que hace el endpoint
-- /api/v1/dashboard/financiamiento-tendencia-mensual
-- Últimos 12 meses por defecto
-- 
-- ⚠️ IMPORTANTE: El backend usa fecha_registro (NO fecha_aprobacion)
-- ⚠️ IMPORTANTE: Solo cuenta préstamos con estado = 'APROBADO'

SELECT 
    EXTRACT(YEAR FROM fecha_registro)::integer AS año,
    EXTRACT(MONTH FROM fecha_registro)::integer AS mes,
    TO_CHAR(fecha_registro, 'Mon YYYY') AS "Mes Año",
    COUNT(*) AS cantidad_prestamos,
    SUM(total_financiamiento) AS monto_total,
    ROUND(AVG(total_financiamiento), 2) AS promedio_por_prestamo
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'
    AND fecha_registro >= CURRENT_DATE - INTERVAL '12 months'
    AND fecha_registro <= CURRENT_DATE
GROUP BY 
    EXTRACT(YEAR FROM fecha_registro),
    EXTRACT(MONTH FROM fecha_registro),
    TO_CHAR(fecha_registro, 'Mon YYYY')
ORDER BY 
    año ASC,
    mes ASC;

-- ============================================================
-- 3B. CONSULTA SIMPLIFICADA PARA VERIFICAR RÁPIDO
-- ============================================================
-- Muestra solo los datos esenciales del gráfico

SELECT 
    TO_CHAR(fecha_registro, 'YYYY-MM') AS "Mes",
    COUNT(*) AS "Cantidad",
    SUM(total_financiamiento) AS "Total Financiamiento"
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'
GROUP BY 
    TO_CHAR(fecha_registro, 'YYYY-MM')
ORDER BY 
    "Mes" DESC
LIMIT 12;

-- ============================================================
-- 4. CONSULTA PARA UN AÑO ESPECÍFICO (2025)
-- ============================================================
-- Similar a la consulta anterior pero filtrando por año 2025

SELECT 
    EXTRACT(YEAR FROM fecha_registro)::integer AS año,
    EXTRACT(MONTH FROM fecha_registro)::integer AS mes,
    TO_CHAR(fecha_registro, 'Mon YYYY') AS "Mes Año",
    COUNT(*) AS cantidad_prestamos,
    SUM(total_financiamiento) AS monto_total,
    ROUND(AVG(total_financiamiento), 2) AS promedio_por_prestamo
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'
    AND EXTRACT(YEAR FROM fecha_registro) = 2025
GROUP BY 
    EXTRACT(YEAR FROM fecha_registro),
    EXTRACT(MONTH FROM fecha_registro),
    TO_CHAR(fecha_registro, 'Mon YYYY')
ORDER BY 
    mes ASC;

-- ============================================================
-- 5. CONSULTA CON FILTROS ADICIONALES (EJEMPLO)
-- ============================================================
-- Incluye filtros por analista, concesionario o modelo si los necesitas

SELECT 
    EXTRACT(YEAR FROM fecha_registro)::integer AS año,
    EXTRACT(MONTH FROM fecha_registro)::integer AS mes,
    TO_CHAR(fecha_registro, 'Mon YYYY') AS "Mes Año",
    -- Opcional: descomenta para ver por analista
    -- COALESCE(analista, producto_financiero) AS analista,
    -- concesionario,
    -- producto AS modelo,
    COUNT(*) AS cantidad_prestamos,
    SUM(total_financiamiento) AS monto_total
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'
    AND fecha_registro >= CURRENT_DATE - INTERVAL '12 months'
    AND fecha_registro <= CURRENT_DATE
    -- Descomenta para filtrar por analista específico:
    -- AND (analista = 'NOMBRE_ANALISTA' OR producto_financiero = 'NOMBRE_ANALISTA')
    -- Descomenta para filtrar por concesionario:
    -- AND concesionario = 'NOMBRE_CONCESIONARIO'
    -- Descomenta para filtrar por modelo:
    -- AND (producto = 'MODELO' OR modelo_vehiculo = 'MODELO')
GROUP BY 
    EXTRACT(YEAR FROM fecha_registro),
    EXTRACT(MONTH FROM fecha_registro),
    TO_CHAR(fecha_registro, 'Mon YYYY')
    -- Opcional: incluye en GROUP BY si descomentaste arriba
    -- , COALESCE(analista, producto_financiero)
    -- , concesionario
    -- , producto
ORDER BY 
    año ASC,
    mes ASC;

-- ============================================================
-- 6. VERIFICAR DATOS DETALLADOS POR MES (EJEMPLO NOVIEMBRE 2025)
-- ============================================================
-- Si necesitas ver los préstamos individuales de un mes específico

SELECT 
    id,
    cedula,
    nombres,
    fecha_registro,
    total_financiamiento,
    estado,
    COALESCE(analista, producto_financiero) AS analista,
    concesionario,
    producto AS modelo,
    numero_cuotas,
    modalidad_pago
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'
    AND EXTRACT(YEAR FROM fecha_registro) = 2025
    AND EXTRACT(MONTH FROM fecha_registro) = 11  -- Noviembre
ORDER BY 
    fecha_registro DESC,
    total_financiamiento DESC;

-- ============================================================
-- 7. RESUMEN DE DATOS POR ESTADO
-- ============================================================
-- Verifica la distribución de préstamos por estado y fecha

SELECT 
    estado,
    COUNT(*) AS total_prestamos,
    SUM(total_financiamiento) AS total_financiamiento,
    MIN(fecha_registro) AS fecha_mas_antigua,
    MAX(fecha_registro) AS fecha_mas_reciente,
    COUNT(CASE WHEN EXTRACT(YEAR FROM fecha_registro) = 2025 THEN 1 END) AS prestamos_2025
FROM 
    prestamos
GROUP BY 
    estado
ORDER BY 
    total_prestamos DESC;

-- ============================================================
-- 8. VERIFICAR CONSISTENCIA DE FECHAS
-- ============================================================
-- Identifica posibles problemas con fechas nulas o inconsistentes

SELECT 
    'Total registros' AS tipo,
    COUNT(*) AS cantidad
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'

UNION ALL

SELECT 
    'Con fecha_registro NULL' AS tipo,
    COUNT(*) AS cantidad
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'
    AND fecha_registro IS NULL

UNION ALL

SELECT 
    'Con total_financiamiento NULL' AS tipo,
    COUNT(*) AS cantidad
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'
    AND total_financiamiento IS NULL

UNION ALL

SELECT 
    'Con total_financiamiento <= 0' AS tipo,
    COUNT(*) AS cantidad
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'
    AND (total_financiamiento IS NULL OR total_financiamiento <= 0);

-- ============================================================
-- NOTAS IMPORTANTES:
-- ============================================================
-- 1. TABLA: prestamos (plural, no singular)
-- 2. COLUMNA DE FECHA: fecha_registro (NO fecha_aprobacion)
-- 3. COLUMNA DE MONTO: total_financiamiento
-- 4. FILTRO PRINCIPAL: estado = 'APROBADO'
-- 5. AGRUPACIÓN: Por año y mes usando EXTRACT
-- 6. RANGO: Últimos 12 meses por defecto (configurable)
-- ============================================================

