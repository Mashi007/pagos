-- ============================================================================
-- VERIFICAR SI HAY PRÉSTAMOS CON CÉDULA V30596349
-- QUE TENGAN FECHA 24/05/2025 EN ALGUNA DE SUS COLUMNAS DE FECHA
-- ============================================================================

SELECT 
    id,
    cedula,
    nombres,
    estado,
    total_financiamiento,
    numero_cuotas,
    
    -- TODAS LAS FECHAS
    fecha_requerimiento,
    fecha_registro,
    DATE(fecha_registro) AS fecha_registro_solo_fecha,
    fecha_aprobacion,
    DATE(fecha_aprobacion) AS fecha_aprobacion_solo_fecha,
    fecha_base_calculo,
    fecha_actualizacion,
    DATE(fecha_actualizacion) AS fecha_actualizacion_solo_fecha,
    
    -- VERIFICACIÓN: ¿Qué fecha coincide con 24/05/2025?
    CASE 
        WHEN fecha_requerimiento = '2025-05-24' THEN '✅ fecha_requerimiento = 24/05/2025'
        WHEN DATE(fecha_registro) = '2025-05-24' THEN '✅ fecha_registro = 24/05/2025'
        WHEN DATE(fecha_aprobacion) = '2025-05-24' THEN '✅ fecha_aprobacion = 24/05/2025'
        WHEN fecha_base_calculo = '2025-05-24' THEN '✅ fecha_base_calculo = 24/05/2025'
        WHEN DATE(fecha_actualizacion) = '2025-05-24' THEN '✅ fecha_actualizacion = 24/05/2025'
        ELSE '❌ NO tiene fecha 24/05/2025'
    END AS fecha_encontrada,
    
    -- VERIFICACIÓN DETALLADA DE CADA FECHA
    CASE WHEN fecha_requerimiento = '2025-05-24' THEN 'SÍ' ELSE 'NO' END AS tiene_requerimiento_24_05,
    CASE WHEN DATE(fecha_registro) = '2025-05-24' THEN 'SÍ' ELSE 'NO' END AS tiene_registro_24_05,
    CASE WHEN DATE(fecha_aprobacion) = '2025-05-24' THEN 'SÍ' ELSE 'NO' END AS tiene_aprobacion_24_05,
    CASE WHEN fecha_base_calculo = '2025-05-24' THEN 'SÍ' ELSE 'NO' END AS tiene_base_calculo_24_05,
    CASE WHEN DATE(fecha_actualizacion) = '2025-05-24' THEN 'SÍ' ELSE 'NO' END AS tiene_actualizacion_24_05
    
FROM prestamos
WHERE cedula = 'V30596349'
ORDER BY id;

