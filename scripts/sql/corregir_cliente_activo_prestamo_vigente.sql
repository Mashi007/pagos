-- ======================================================================
-- SCRIPT PARA CORREGIR CLIENTE CON PRESTAMO VIGENTE
-- ======================================================================
-- Caso: Cliente ID 25728 (V20428105) - PEDRO JAVIER ALDANA RAMIREZ
-- Problema: Cliente en estado INACTIVO con préstamo APROBADO (vigente)
-- Solución: Cliente debe estar ACTIVO porque tiene préstamo vigente
-- ======================================================================

-- ======================================================================
-- 1. VERIFICAR ESTADO ACTUAL ANTES DE LA CORRECCION
-- ======================================================================

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

-- ======================================================================
-- 2. ACTUALIZAR CLIENTE A ESTADO 'ACTIVO'
-- ======================================================================
-- El cliente tiene un préstamo aprobado (vigente), por lo tanto debe estar ACTIVO
-- ======================================================================

UPDATE clientes 
SET estado = 'ACTIVO',
    activo = TRUE,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE id = 25728
  AND estado = 'INACTIVO'
  AND EXISTS (
      SELECT 1 FROM prestamos p 
      WHERE p.cedula = clientes.cedula 
      AND p.estado = 'APROBADO'
  );

-- ======================================================================
-- 3. VERIFICAR ESTADO DESPUES DE LA CORRECCION
-- ======================================================================

SELECT 
    'DESPUES' AS momento,
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

-- ======================================================================
-- 4. VERIFICAR REGLA DE NEGOCIO: CLIENTES ACTIVOS CON PRESTAMOS APROBADOS
-- ======================================================================

SELECT 
    'Verificacion regla de negocio' AS tipo_verificacion,
    COUNT(*) AS total_clientes_activos_con_prestamos
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.estado = 'ACTIVO'
  AND c.activo = TRUE
  AND p.estado = 'APROBADO';

-- ======================================================================
-- 5. VERIFICAR QUE NO QUEDEN CLIENTES INACTIVOS CON PRESTAMOS APROBADOS
-- ======================================================================

SELECT 
    'Clientes INACTIVOS con prestamos aprobados' AS tipo_verificacion,
    COUNT(*) AS total_casos_anomalos
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO';

-- ======================================================================
-- 6. DETALLE COMPLETO DEL CLIENTE CORREGIDO
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_cliente,
    c.activo,
    c.fecha_registro,
    c.fecha_actualizacion,
    p.id AS prestamo_id,
    p.estado AS estado_prestamo,
    p.total_financiamiento,
    p.numero_cuotas,
    p.fecha_aprobacion,
    COUNT(cu.id) AS total_cuotas_generadas,
    COALESCE(SUM(cu.total_pagado), 0) AS total_pagado,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.id = 25728
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo, 
         c.fecha_registro, c.fecha_actualizacion,
         p.id, p.estado, p.total_financiamiento, p.numero_cuotas, p.fecha_aprobacion;

-- ======================================================================
-- RESUMEN:
-- ======================================================================
-- Este script corrige el caso del cliente que tiene un préstamo aprobado
-- (vigente) pero estaba en estado INACTIVO. La corrección cambia el
-- estado a ACTIVO porque el préstamo está vigente, aunque no haya pagos.
-- 
-- Regla de negocio aplicada:
-- - Clientes ACTIVOS = Tienen préstamos aprobados (vigentes)
-- - Clientes INACTIVOS = No tienen préstamos aprobados (pasivos)
-- - Clientes FINALIZADOS = Completaron su ciclo de préstamo
-- ======================================================================
