-- =====================================================
-- SCRIPT DE VALIDACIÓN DE DATOS ANTES DE MIGRACIÓN (VERSIÓN SEGURA)
-- Ejecutar en DBeaver ANTES de aplicar las migraciones
-- Esta versión maneja correctamente tablas opcionales
-- =====================================================

-- 1. VALIDAR pagos.prestamo_id - Verificar pagos con prestamo_id inválido
SELECT 
    COUNT(*) as total_pagos,
    COUNT(DISTINCT prestamo_id) as prestamos_unicos,
    COUNT(*) FILTER (WHERE prestamo_id IS NOT NULL) as pagos_con_prestamo_id,
    COUNT(*) FILTER (WHERE prestamo_id IS NOT NULL AND prestamo_id NOT IN (SELECT id FROM prestamos)) as pagos_con_prestamo_id_invalido
FROM pagos;

-- Mostrar pagos con prestamo_id inválido
SELECT 
    p.id,
    p.cedula,
    p.prestamo_id,
    p.monto_pagado,
    p.fecha_pago
FROM pagos p
LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE p.prestamo_id IS NOT NULL 
  AND pr.id IS NULL
ORDER BY p.id;

-- 2. VALIDAR pagos.cedula - Verificar pagos con cédulas que no existen en clientes
SELECT 
    COUNT(*) as total_pagos,
    COUNT(DISTINCT cedula) as cedulas_unicas,
    COUNT(*) FILTER (WHERE cedula NOT IN (SELECT cedula FROM clientes)) as pagos_con_cedula_invalida
FROM pagos;

-- Mostrar pagos con cédulas inválidas
SELECT 
    p.id,
    p.cedula,
    p.prestamo_id,
    p.monto_pagado,
    p.fecha_pago
FROM pagos p
WHERE p.cedula NOT IN (SELECT cedula FROM clientes)
ORDER BY p.id;

-- 3. VALIDAR prestamos_evaluacion.prestamo_id - Verificar evaluaciones con prestamo_id inválido
SELECT 
    COUNT(*) as total_evaluaciones,
    COUNT(*) FILTER (WHERE prestamo_id NOT IN (SELECT id FROM prestamos)) as evaluaciones_con_prestamo_id_invalido
FROM prestamos_evaluacion;

-- Mostrar evaluaciones con prestamo_id inválido
SELECT 
    pe.id,
    pe.prestamo_id,
    pe.cedula,
    pe.puntuacion_total,
    pe.clasificacion_riesgo
FROM prestamos_evaluacion pe
LEFT JOIN prestamos pr ON pe.prestamo_id = pr.id
WHERE pr.id IS NULL
ORDER BY pe.id;

-- 4. VALIDAR pagos_auditoria.pago_id - Verificar auditorías con pago_id inválido
-- ⚠️ NOTA: Esta tabla puede no existir. Si no existe, se puede crear con la migración.
DO $$
DECLARE
    v_count_invalidos INTEGER := 0;
    v_total INTEGER := 0;
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'pagos_auditoria') THEN
        RAISE NOTICE '✅ Tabla pagos_auditoria existe, validando datos...';
        
        EXECUTE 'SELECT COUNT(*) FROM pagos_auditoria' INTO v_total;
        EXECUTE 'SELECT COUNT(*) FROM pagos_auditoria pa LEFT JOIN pagos p ON pa.pago_id = p.id WHERE p.id IS NULL' INTO v_count_invalidos;
        
        RAISE NOTICE '   Total auditorías de pagos: %', v_total;
        RAISE NOTICE '   Auditorías con pago_id inválido: %', v_count_invalidos;
        
        IF v_count_invalidos > 0 THEN
            RAISE NOTICE '   ⚠️ Se encontraron % auditorías con pago_id inválido', v_count_invalidos;
        ELSE
            RAISE NOTICE '   ✅ Todas las auditorías tienen pago_id válido';
        END IF;
    ELSE
        RAISE NOTICE '⚠️ Tabla pagos_auditoria NO existe - se creará con la migración (no es un problema)';
    END IF;
END $$;

-- 5. VALIDAR prestamos_auditoria.prestamo_id - Verificar auditorías con prestamo_id inválido
-- ⚠️ NOTA: Esta tabla puede no existir. Si no existe, se puede crear con la migración.
DO $$
DECLARE
    v_count_invalidos INTEGER := 0;
    v_total INTEGER := 0;
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'prestamos_auditoria') THEN
        RAISE NOTICE '✅ Tabla prestamos_auditoria existe, validando datos...';
        
        EXECUTE 'SELECT COUNT(*) FROM prestamos_auditoria' INTO v_total;
        EXECUTE 'SELECT COUNT(*) FROM prestamos_auditoria pra LEFT JOIN prestamos pr ON pra.prestamo_id = pr.id WHERE pr.id IS NULL' INTO v_count_invalidos;
        
        RAISE NOTICE '   Total auditorías de préstamos: %', v_total;
        RAISE NOTICE '   Auditorías con prestamo_id inválido: %', v_count_invalidos;
        
        IF v_count_invalidos > 0 THEN
            RAISE NOTICE '   ⚠️ Se encontraron % auditorías con prestamo_id inválido', v_count_invalidos;
        ELSE
            RAISE NOTICE '   ✅ Todas las auditorías tienen prestamo_id válido';
        END IF;
    ELSE
        RAISE NOTICE '⚠️ Tabla prestamos_auditoria NO existe - se creará con la migración (no es un problema)';
    END IF;
END $$;

-- 6. VALIDAR prestamos.concesionario - Verificar concesionarios que no existen en tabla concesionarios
SELECT 
    COUNT(DISTINCT concesionario) as concesionarios_unicos_en_prestamos,
    COUNT(DISTINCT concesionario) FILTER (WHERE concesionario IS NOT NULL AND concesionario NOT IN (SELECT nombre FROM concesionarios)) as concesionarios_invalidos
FROM prestamos;

-- Mostrar prestamos con concesionarios inválidos
SELECT DISTINCT
    p.concesionario,
    COUNT(*) as cantidad_prestamos
FROM prestamos p
WHERE p.concesionario IS NOT NULL 
  AND p.concesionario NOT IN (SELECT nombre FROM concesionarios)
GROUP BY p.concesionario
ORDER BY cantidad_prestamos DESC;

-- 7. VALIDAR prestamos.analista - Verificar analistas que no existen en tabla analistas
SELECT 
    COUNT(DISTINCT analista) as analistas_unicos_en_prestamos,
    COUNT(DISTINCT analista) FILTER (WHERE analista IS NOT NULL AND analista NOT IN (SELECT nombre FROM analistas)) as analistas_invalidos
FROM prestamos;

-- Mostrar prestamos con analistas inválidos
SELECT DISTINCT
    p.analista,
    COUNT(*) as cantidad_prestamos
FROM prestamos p
WHERE p.analista IS NOT NULL 
  AND p.analista NOT IN (SELECT nombre FROM analistas)
GROUP BY p.analista
ORDER BY cantidad_prestamos DESC;

-- 8. VALIDAR prestamos.modelo_vehiculo - Verificar modelos que no existen en tabla modelos_vehiculos
SELECT 
    COUNT(DISTINCT modelo_vehiculo) as modelos_unicos_en_prestamos,
    COUNT(DISTINCT modelo_vehiculo) FILTER (WHERE modelo_vehiculo IS NOT NULL AND modelo_vehiculo NOT IN (SELECT modelo FROM modelos_vehiculos)) as modelos_invalidos
FROM prestamos;

-- Mostrar prestamos con modelos inválidos
SELECT DISTINCT
    p.modelo_vehiculo,
    COUNT(*) as cantidad_prestamos
FROM prestamos p
WHERE p.modelo_vehiculo IS NOT NULL 
  AND p.modelo_vehiculo NOT IN (SELECT modelo FROM modelos_vehiculos)
GROUP BY p.modelo_vehiculo
ORDER BY cantidad_prestamos DESC;

-- =====================================================
-- RESUMEN DE VALIDACIÓN
-- =====================================================
SELECT 
    'pagos con prestamo_id inválido' as tipo,
    COUNT(*) as cantidad
FROM pagos p
LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE p.prestamo_id IS NOT NULL AND pr.id IS NULL

UNION ALL

SELECT 
    'pagos con cedula inválida' as tipo,
    COUNT(*) as cantidad
FROM pagos p
WHERE p.cedula NOT IN (SELECT cedula FROM clientes)

UNION ALL

SELECT 
    'evaluaciones con prestamo_id inválido' as tipo,
    COUNT(*) as cantidad
FROM prestamos_evaluacion pe
LEFT JOIN prestamos pr ON pe.prestamo_id = pr.id
WHERE pr.id IS NULL;

-- Nota: Las auditorías se validan en los bloques DO $$ anteriores
-- Si las tablas de auditoría no existen, no es un problema

