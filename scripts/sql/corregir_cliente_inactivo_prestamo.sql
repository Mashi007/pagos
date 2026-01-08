-- ======================================================================
-- SCRIPT PARA CORREGIR CLIENTE INACTIVO CON PRESTAMO APROBADO
-- ======================================================================
-- Caso: Cliente ID 25728 (V20428105) - PEDRO JAVIER ALDANA RAMIREZ
-- Problema: Cliente en estado INACTIVO con préstamo APROBADO
-- Regla de negocio: Clientes INACTIVOS (pasivos) NO deben tener préstamos aprobados
-- ======================================================================

-- ======================================================================
-- OPCION 1: CAMBIAR ESTADO DEL CLIENTE A 'FINALIZADO'
-- ======================================================================
-- Usar esta opción si el préstamo es válido y el cliente completó su ciclo
-- (aunque no haya pagos, el préstamo fue aprobado y tiene cuotas generadas)
-- ======================================================================

-- Verificar datos antes de la corrección
SELECT 
    'ANTES' AS momento,
    c.id,
    c.cedula,
    c.nombres,
    c.estado,
    c.activo,
    c.fecha_actualizacion,
    COUNT(p.id) AS prestamos_aprobados
FROM clientes c
LEFT JOIN prestamos p ON c.cedula = p.cedula AND p.estado = 'APROBADO'
WHERE c.id = 25728
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo, c.fecha_actualizacion;

-- ACTUALIZAR ESTADO DEL CLIENTE A 'FINALIZADO'
-- DESCOMENTAR LA SIGUIENTE LÍNEA PARA EJECUTAR:
-- UPDATE clientes 
-- SET estado = 'FINALIZADO',
--     activo = FALSE,
--     fecha_actualizacion = CURRENT_TIMESTAMP
-- WHERE id = 25728
--   AND estado = 'INACTIVO';

-- Verificar datos después de la corrección
-- SELECT 
--     'DESPUES' AS momento,
--     c.id,
--     c.cedula,
--     c.nombres,
--     c.estado,
--     c.activo,
--     c.fecha_actualizacion,
--     COUNT(p.id) AS prestamos_aprobados
-- FROM clientes c
-- LEFT JOIN prestamos p ON c.cedula = p.cedula AND p.estado = 'APROBADO'
-- WHERE c.id = 25728
-- GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo, c.fecha_actualizacion;

-- ======================================================================
-- OPCION 2: CAMBIAR ESTADO DEL PRESTAMO A 'CANCELADO' O 'RECHAZADO'
-- ======================================================================
-- Usar esta opción si el préstamo no debería estar aprobado
-- (el cliente es realmente pasivo y no concretó la opción)
-- ======================================================================

-- Verificar préstamo antes de la corrección
-- SELECT 
--     'ANTES' AS momento,
--     p.id,
--     p.cedula,
--     p.estado,
--     p.total_financiamiento,
--     p.fecha_aprobacion,
--     COUNT(cu.id) AS total_cuotas
-- FROM prestamos p
-- LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
-- WHERE p.id = 7267
-- GROUP BY p.id, p.cedula, p.estado, p.total_financiamiento, p.fecha_aprobacion;

-- ACTUALIZAR ESTADO DEL PRESTAMO A 'CANCELADO'
-- DESCOMENTAR LA SIGUIENTE LÍNEA PARA EJECUTAR:
-- UPDATE prestamos 
-- SET estado = 'CANCELADO',
--     fecha_actualizacion = CURRENT_TIMESTAMP
-- WHERE id = 7267
--   AND estado = 'APROBADO'
--   AND cedula = 'V20428105';

-- Verificar préstamo después de la corrección
-- SELECT 
--     'DESPUES' AS momento,
--     p.id,
--     p.cedula,
--     p.estado,
--     p.total_financiamiento,
--     p.fecha_aprobacion,
--     COUNT(cu.id) AS total_cuotas
-- FROM prestamos p
-- LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
-- WHERE p.id = 7267
-- GROUP BY p.id, p.cedula, p.estado, p.total_financiamiento, p.fecha_aprobacion;

-- ======================================================================
-- OPCION 3: VERIFICAR REGLA DE NEGOCIO DESPUES DE LA CORRECCION
-- ======================================================================
-- Ejecutar esta consulta después de aplicar la corrección para verificar
-- que la regla de negocio se cumple correctamente
-- ======================================================================

-- Verificar que no queden clientes INACTIVOS con préstamos aprobados
-- SELECT 
--     COUNT(*) AS clientes_inactivos_con_prestamos
-- FROM clientes c
-- INNER JOIN prestamos p ON c.cedula = p.cedula
-- WHERE c.estado = 'INACTIVO'
--   AND p.estado = 'APROBADO';

-- ======================================================================
-- INSTRUCCIONES:
-- ======================================================================
-- 1. Revisar los datos ANTES de ejecutar cualquier UPDATE
-- 2. Decidir qué opción aplicar según el caso de negocio:
--    - OPCION 1: Si el préstamo es válido → cambiar cliente a FINALIZADO
--    - OPCION 2: Si el préstamo no debería estar aprobado → cancelar préstamo
-- 3. Descomentar la línea UPDATE correspondiente
-- 4. Ejecutar el UPDATE
-- 5. Verificar los datos DESPUES con las consultas de verificación
-- 6. Ejecutar la verificación final de la regla de negocio
-- ======================================================================
-- IMPORTANTE: Hacer backup de la base de datos antes de ejecutar updates
-- ======================================================================
