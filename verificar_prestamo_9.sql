-- ============================================
-- VERIFICACIÓN COMPLETA PRÉSTAMO #9
-- ============================================

-- 1. Ver estado actual del préstamo
SELECT 
    id,
    cedula,
    nombres,
    estado,
    total_financiamiento,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    fecha_aprobacion,
    fecha_base_calculo,
    usuario_aprobador
FROM 
    prestamos 
WHERE 
    id = 9;

-- 2. Ver cuantas cuotas tiene actualmente
SELECT 
    COUNT(*) as total_cuotas,
    MIN(numero_cuota) as primera_cuota,
    MAX(numero_cuota) as ultima_cuota
FROM 
    cuotas 
WHERE 
    prestamo_id = 9;

-- 3. Ver detalle de las cuotas
SELECT 
    numero_cuota,
    fecha_vencimiento,
    monto_cuota,
    estado
FROM 
    cuotas 
WHERE 
    prestamo_id = 9
ORDER BY 
    numero_cuota
LIMIT 5;

-- 4. Ver evaluación asociada
SELECT 
    decision_final,
    puntuacion_total,
    clasificacion_riesgo,
    plazo_maximo
FROM 
    prestamos_evaluacion
WHERE 
    prestamo_id = 9
ORDER BY 
    id DESC
LIMIT 1;

