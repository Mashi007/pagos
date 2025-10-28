-- ============================================
-- VERIFICACIÓN COMPLETA: APROBACIÓN AUTOMÁTICA
-- ============================================
-- Ejecutar en DBeaver para auditar el proceso de aprobación automática
-- Fecha: 28/10/2025
-- Préstamo #9: Juan García (J12345678)

-- ============================================
-- 1. VERIFICAR ESTADO DEL PRÉSTAMO
-- ============================================
SELECT 
    id,
    cedula,
    nombres,
    estado,
    total_financiamiento,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    fecha_requerimiento,
    fecha_aprobacion,
    fecha_base_calculo,
    usuario_proponente,
    usuario_aprobador,
    observaciones,
    created_at,
    updated_at
FROM 
    prestamos 
WHERE 
    id = 9 OR cedula = 'J12345678'
ORDER BY 
    id DESC;

-- Esperado:
-- estado: 'APROBADO'
-- fecha_aprobacion: 2025-10-28
-- fecha_base_calculo: 2025-11-28 (hoy + 1 mes)
-- usuario_aprobador: email del admin
-- observaciones: contiene "Aprobación automática"

-- ============================================
-- 2. VERIFICAR EVALUACIÓN DE RIESGO
-- ============================================
SELECT 
    id,
    prestamo_id,
    puntuacion_total,
    clasificacion_riesgo,
    decision_final,
    tasa_interes_aplicada,
    plazo_maximo,
    enganche_minimo,
    requisitos_adicionales,
    created_at
FROM 
    prestamos_evaluacion 
WHERE 
    prestamo_id = 9
ORDER BY 
    created_at DESC
LIMIT 1;

-- Esperado:
-- decision_final: 'APROBADO_AUTOMATICO'
-- clasificacion_riesgo: 'A'
-- puntuacion_total: 96.50 (aproximado)
-- plazo_maximo: mayor a 0
-- tasa_interes_aplicada: >= 0

-- ============================================
-- 3. VERIFICAR TABLA DE AMORTIZACIÓN (CUOTAS)
-- ============================================
SELECT 
    id,
    prestamo_id,
    numero_cuota,
    fecha_vencimiento,
    monto_capital,
    monto_interes,
    monto_cuota,
    saldo_capital_inicial,
    saldo_capital_final,
    estado,
    created_at
FROM 
    cuotas 
WHERE 
    prestamo_id = 9
ORDER BY 
    numero_cuota;

-- Esperado:
-- Debe haber 12 cuotas (numero_cuota: 1-12)
-- estado: 'PENDIENTE' para todas
-- fecha_vencimiento: fechas futuras

-- ============================================
-- 4. VERIFICAR CAMBIOS DE ESTADO (AUDITORÍA)
-- ============================================
SELECT 
    id,
    prestamo_id,
    cedula,
    usuario,
    accion,
    campo_modificado,
    valor_anterior,
    valor_nuevo,
    estado_anterior,
    estado_nuevo,
    created_at
FROM 
    prestamo_auditoria 
WHERE 
    prestamo_id = 9
ORDER BY 
    created_at DESC;

-- Esperado:
-- Debe haber registro con:
-- accion: 'APLICAR_CONDICIONES' o 'CAMBIAR_ESTADO'
-- estado_anterior: 'DRAFT' o 'BORRADOR'
-- estado_nuevo: 'APROBADO'

-- ============================================
-- 5. VERIFICAR ÚLTIMAS ACTUALIZACIONES
-- ============================================
SELECT 
    p.id,
    p.estado,
    p.updated_at,
    e.decision_final,
    e.puntuacion_total,
    COUNT(c.id) as total_cuotas
FROM 
    prestamos p
LEFT JOIN 
    prestamos_evaluacion e ON e.prestamo_id = p.id
LEFT JOIN 
    cuotas c ON c.prestamo_id = p.id
WHERE 
    p.id = 9
GROUP BY 
    p.id, p.estado, p.updated_at, e.decision_final, e.puntuacion_total;

-- Esperado:
-- estado: 'APROBADO'
-- decision_final: 'APROBADO_AUTOMATICO'
-- total_cuotas: 12
-- updated_at: Fecha reciente (hoy)

-- ============================================
-- 6. VERIFICAR CONDICIONES APLICADAS
-- ============================================
-- Comparar datos de evaluación vs préstamo
SELECT 
    'Evaluación' as origen,
    e.prestamo_id,
    e.decision_final,
    e.plazo_maximo,
    e.tasa_interes_aplicada,
    e.puntuacion_total
FROM 
    prestamos_evaluacion e
WHERE 
    e.prestamo_id = 9
    
UNION ALL

SELECT 
    'Préstamo' as origen,
    p.id as prestamo_id,
    p.estado as decision_final,
    CAST(p.numero_cuotas AS INTEGER) as plazo_maximo,
    p.tasa_interes as tasa_interes_aplicada,
    0 as puntuacion_total
FROM 
    prestamos p
WHERE 
    p.id = 9;

-- Esperado:
-- Debe coincidir:
-- plazo_maximo de evaluación = numero_cuotas del préstamo
-- tasa_interes de evaluación ≈ tasa_interes del préstamo

-- ============================================
-- DIAGNÓSTICO
-- ============================================
-- Si algo falla, revisar estos indicadores:

-- ¿El préstamo está en estado BORRADOR?
SELECT '❌ ERROR: Préstamo no actualizado' as diagnostico
WHERE EXISTS (
    SELECT 1 FROM prestamos WHERE id = 9 AND estado != 'APROBADO'
);

-- ¿Existe la evaluación?
SELECT '❌ ERROR: No existe evaluación' as diagnostico
WHERE NOT EXISTS (
    SELECT 1 FROM prestamos_evaluacion WHERE prestamo_id = 9
);

-- ¿Se generaron cuotas?
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '❌ ERROR: No se generaron cuotas'
        WHEN COUNT(*) < 12 THEN CONCAT('⚠️ ADVERTENCIA: Solo ', COUNT(*), ' cuotas generadas')
        ELSE '✅ OK: Todas las cuotas generadas'
    END as diagnostico
FROM 
    cuotas 
WHERE 
    prestamo_id = 9;

