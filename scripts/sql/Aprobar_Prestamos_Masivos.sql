-- ============================================
-- APROBAR PRÉSTAMOS MASIVOS Y CONFIGURAR DATOS
-- ============================================
-- Fecha: 2025-10-31
-- Descripción: 
-- 1. Aprobar todos los préstamos que están en DRAFT u otros estados
-- 2. Asignar fecha_aprobacion, usuario_aprobador, fecha_base_calculo
-- 3. Preparar para generar tabla de amortización
-- ============================================

-- ============================================
-- PASO 1: VERIFICAR ESTADO ACTUAL
-- ============================================
SELECT 
    estado,
    COUNT(*) AS cantidad,
    COUNT(CASE WHEN fecha_aprobacion IS NULL THEN 1 END) AS sin_aprobacion,
    COUNT(CASE WHEN fecha_base_calculo IS NULL THEN 1 END) AS sin_fecha_base,
    COUNT(CASE WHEN usuario_aprobador IS NULL THEN 1 END) AS sin_aprobador
FROM public.prestamos
GROUP BY estado
ORDER BY estado;

-- Ver algunos ejemplos
SELECT 
    id,
    cedula,
    nombres,
    estado,
    total_financiamiento,
    numero_cuotas,
    tasa_interes,
    fecha_requerimiento,
    fecha_aprobacion,
    fecha_base_calculo,
    usuario_proponente,
    usuario_aprobador
FROM public.prestamos
WHERE estado != 'APROBADO' OR fecha_aprobacion IS NULL
ORDER BY id
LIMIT 10;

-- ============================================
-- PASO 2: APROBAR PRÉSTAMOS (CAMBIAR ESTADO)
-- ============================================
-- IMPORTANTE: 
-- - Cambiará todos los préstamos que NO están en 'APROBADO'
-- - Usar 'itmaster@rapicreditca.com' como aprobador por defecto (ajustar si necesario)
-- - fecha_base_calculo será fecha_requerimiento o fecha_registro + 30 días

UPDATE public.prestamos
SET 
    estado = 'APROBADO',
    fecha_aprobacion = COALESCE(fecha_registro, CURRENT_TIMESTAMP),
    usuario_aprobador = COALESCE(usuario_aprobador, 'itmaster@rapicreditca.com'),
    fecha_base_calculo = COALESCE(
        fecha_base_calculo,
        fecha_requerimiento,
        (CURRENT_DATE + INTERVAL '30 days')::date
    ),
    observaciones = COALESCE(
        observaciones,
        'Aprobación masiva automática - ' || CURRENT_TIMESTAMP::text
    ),
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE 
    estado != 'APROBADO' 
    OR fecha_aprobacion IS NULL;

-- ============================================
-- PASO 3: VERIFICAR RESULTADOS DE APROBACIÓN
-- ============================================
SELECT 
    'PRESTAMOS APROBADOS' AS descripcion,
    COUNT(*) AS total,
    COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados,
    COUNT(CASE WHEN fecha_aprobacion IS NOT NULL THEN 1 END) AS con_fecha_aprobacion,
    COUNT(CASE WHEN usuario_aprobador IS NOT NULL THEN 1 END) AS con_aprobador,
    COUNT(CASE WHEN fecha_base_calculo IS NOT NULL THEN 1 END) AS con_fecha_base
FROM public.prestamos;

-- ============================================
-- PASO 4: VERIFICAR PRÉSTAMOS QUE NECESITAN CUOTAS
-- ============================================
-- Prestamos aprobados sin cuotas
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    p.estado,
    p.total_financiamiento,
    p.numero_cuotas,
    p.cuota_periodo,
    p.tasa_interes,
    p.fecha_base_calculo,
    COUNT(c.id) AS cuotas_existentes
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.nombres, p.estado, p.total_financiamiento, 
         p.numero_cuotas, p.cuota_periodo, p.tasa_interes, p.fecha_base_calculo
HAVING COUNT(c.id) = 0 OR COUNT(c.id) != p.numero_cuotas
ORDER BY p.id
LIMIT 20;

-- ============================================
-- PASO 5: RESUMEN FINAL
-- ============================================
SELECT 
    'RESUMEN FINAL' AS titulo,
    (SELECT COUNT(*) FROM public.prestamos) AS total_prestamos,
    (SELECT COUNT(*) FROM public.prestamos WHERE estado = 'APROBADO') AS prestamos_aprobados,
    (SELECT COUNT(*) FROM public.prestamos WHERE fecha_base_calculo IS NOT NULL) AS con_fecha_base,
    (SELECT COUNT(DISTINCT prestamo_id) FROM public.cuotas) AS prestamos_con_cuotas,
    (SELECT COUNT(*) FROM public.cuotas) AS total_cuotas_generadas;

-- ============================================
-- NOTAS IMPORTANTES
-- ============================================
-- 
-- 1. Este script solo APRUEBA los préstamos y configura fechas
-- 2. Para GENERAR LAS CUOTAS (tabla de amortización), ejecutar:
--    - Script Python: scripts/python/Generar_Cuotas_Masivas.py
--    - O usar API: POST /api/v1/prestamos/{id}/generar-amortizacion
-- 
-- 3. Verificar que todos los préstamos tengan:
--    - estado = 'APROBADO' ✓
--    - fecha_base_calculo no NULL ✓
--    - numero_cuotas > 0 ✓
--    - total_financiamiento > 0 ✓
--
-- ============================================

