-- ============================================
-- VERIFICAR TABLA: prestamos_evaluacion
-- ============================================

-- Ver estructura de la tabla
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'prestamos_evaluacion'
ORDER BY ordinal_position;

-- Ver si existe la tabla y cuántos registros tiene
SELECT COUNT(*) AS total_evaluaciones
FROM prestamos_evaluacion;

-- Ver últimos 10 registros (si existen)
SELECT * FROM prestamos_evaluacion ORDER BY id DESC LIMIT 10;

-- Ver relación entre préstamos y evaluaciones (JOIN)
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.estado AS estado_prestamo,
    p.total_financiamiento,
    p.cuota_periodo,
    e.id AS evaluacion_id,
    e.puntuacion_total,
    e.clasificacion_riesgo,
    e.decision_final,
    e.tasa_interes_aplicada,
    e.plazo_maximo
FROM prestamos p
LEFT JOIN prestamos_evaluacion e ON p.id = e.prestamo_id
ORDER BY p.id DESC
LIMIT 10;

