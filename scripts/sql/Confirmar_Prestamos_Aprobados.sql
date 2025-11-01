-- CONFIRMACION: TODOS LOS PRESTAMOS ESTAN APROBADOS
-- Verificacion especifica para prestamos migrados de otro sistema

-- PASO 1: DISTRIBUCION POR ESTADO
SELECT 
    estado,
    COUNT(*) AS cantidad_prestamos,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS porcentaje,
    COALESCE(SUM(total_financiamiento), 0) AS total_financiamiento,
    COALESCE(AVG(total_financiamiento), 0) AS promedio_financiamiento
FROM prestamos
GROUP BY estado
ORDER BY estado;

-- PASO 2: TOTALES Y VERIFICACION
SELECT 
    'Total de prestamos' AS metrica,
    COUNT(*) AS valor,
    CASE 
        WHEN COUNT(*) > 0 THEN 'OK'
        ELSE 'ERROR'
    END AS estado
FROM prestamos

UNION ALL

SELECT 
    'Prestamos APROBADOS' AS metrica,
    COUNT(*) AS valor,
    CASE 
        WHEN COUNT(*) > 0 THEN 'OK'
        ELSE 'ERROR'
    END AS estado
FROM prestamos
WHERE estado = 'APROBADO'

UNION ALL

SELECT 
    'Prestamos NO APROBADOS' AS metrica,
    COUNT(*) AS valor,
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK (Correcto - Todos estan aprobados)'
        ELSE 'ERROR (PROBLEMA: Hay prestamos no aprobados)'
    END AS estado
FROM prestamos
WHERE estado != 'APROBADO' OR estado IS NULL

UNION ALL

SELECT 
    'Porcentaje de aprobados' AS metrica,
    ROUND(
        (COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) * 100.0 / 
         NULLIF(COUNT(*), 0)), 2
    ) AS valor,
    CASE 
        WHEN COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) = COUNT(*) 
            THEN 'OK (100% aprobados)'
        ELSE 'ATENCION (No todos estan aprobados)'
    END AS estado
FROM prestamos;

-- PASO 3: VERIFICACION DETALLADA POR ESTADO
SELECT 
    estado,
    COUNT(*) AS cantidad,
    MIN(fecha_registro) AS fecha_primer_prestamo,
    MAX(fecha_registro) AS fecha_ultimo_prestamo,
    MIN(fecha_aprobacion) AS fecha_primer_aprobacion,
    MAX(fecha_aprobacion) AS fecha_ultima_aprobacion,
    STRING_AGG(DISTINCT CAST(id AS VARCHAR), ', ' ORDER BY CAST(id AS VARCHAR)) AS ejemplo_ids
FROM prestamos
GROUP BY estado
ORDER BY estado;

-- PASO 4: PRESTAMOS CON PROBLEMAS DE ESTADO
SELECT 
    id,
    cedula,
    estado,
    total_financiamiento,
    fecha_registro,
    fecha_aprobacion,
    CASE 
        WHEN estado IS NULL THEN 'Estado NULL'
        WHEN estado NOT IN ('APROBADO', 'DRAFT', 'EN_REVISION', 'EVALUADO', 'RECHAZADO') 
            THEN 'Estado invalido: ' || estado
        ELSE 'Estado valido'
    END AS observacion
FROM prestamos
WHERE estado IS NULL 
    OR estado NOT IN ('APROBADO', 'DRAFT', 'EN_REVISION', 'EVALUADO', 'RECHAZADO')
ORDER BY id
LIMIT 20;

-- PASO 5: RESUMEN FINAL Y CONFIRMACION
WITH resumen AS (
    SELECT 
        COUNT(*) AS total,
        COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados,
        COUNT(CASE WHEN estado != 'APROBADO' OR estado IS NULL THEN 1 END) AS no_aprobados
    FROM prestamos
)
SELECT 
    total AS total_prestamos,
    aprobados AS prestamos_aprobados,
    no_aprobados AS prestamos_no_aprobados,
    CASE 
        WHEN no_aprobados = 0 THEN 'CONFIRMADO: Todos los prestamos estan APROBADOS'
        ELSE 'PROBLEMA: Hay ' || no_aprobados || ' prestamos NO aprobados'
    END AS confirmacion
FROM resumen;

-- PASO 6: EJEMPLOS DE PRESTAMOS
SELECT 
    id,
    cedula,
    estado,
    total_financiamiento,
    numero_cuotas,
    fecha_registro,
    fecha_aprobacion,
    fecha_base_calculo,
    concesionario,
    analista,
    CASE 
        WHEN estado = 'APROBADO' THEN 'OK'
        ELSE 'ERROR'
    END AS estado_icono
FROM prestamos
ORDER BY id
LIMIT 10;

-- PASO 7: CONFIRMACION FINAL
SELECT 
    'Total prestamos: ' || COUNT(*)::VARCHAR AS columna1,
    'Aprobados: ' || COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END)::VARCHAR AS columna2,
    CASE 
        WHEN COUNT(CASE WHEN estado != 'APROBADO' OR estado IS NULL THEN 1 END) = 0 
            THEN 'CONFIRMADO: TODOS LOS PRESTAMOS ESTAN APROBADOS'
        ELSE 'ATENCION: Hay prestamos NO aprobados'
    END AS columna3
FROM prestamos;
