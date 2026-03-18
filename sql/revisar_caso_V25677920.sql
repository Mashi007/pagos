-- =============================================================================
-- Revisión completa del caso V25677920 (cédula)
-- Ejecutar contra la BD (PostgreSQL).
-- Si usas psql: \set cedula_buscar 'V25677920' y sustituir :'cedula_buscar' abajo.
-- Si usas otro cliente: reemplaza 'V25677920' en cada consulta por el valor a buscar.
-- =============================================================================

-- Buscar por cédula (ajustar si en BD está como '25677920' u otro formato)
-- Opción 1: coincidencia exacta o con espacios
-- Opción 2: contiene el número (por si viene con guión, etc.)

-- =============================================================================
-- 1) CLIENTE(S) con esta cédula
-- =============================================================================
SELECT id AS cliente_id, cedula, nombres, telefono, email, direccion, estado, fecha_nacimiento, ocupacion, fecha_registro, fecha_actualizacion
FROM clientes
WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V25677920'))
   OR cedula LIKE '%25677920%';

-- =============================================================================
-- 2) PRÉSTAMOS del cliente (por cliente_id y por cedula en préstamos)
-- =============================================================================
SELECT p.id AS prestamo_id, p.cliente_id, p.cedula, p.nombres,
       p.total_financiamiento, p.numero_cuotas, p.modalidad_pago, p.estado,
       p.fecha_requerimiento, p.fecha_aprobacion::date AS fecha_aprobacion,
       p.fecha_base_calculo, p.fecha_registro::date AS fecha_registro,
       p.analista, p.concesionario, p.modelo_vehiculo, p.producto,
       p.tasa_interes, p.cuota_periodo
FROM prestamos p
WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V25677920')) OR cedula LIKE '%25677920%')
   OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V25677920'))
   OR p.cedula LIKE '%25677920%'
ORDER BY p.id;

-- =============================================================================
-- 3) CUOTAS de esos préstamos (tabla de amortización)
-- =============================================================================
SELECT c.id AS cuota_id, c.prestamo_id, c.numero_cuota, c.fecha_vencimiento, c.fecha_pago,
       c.monto_cuota AS monto, c.total_pagado, c.estado AS estado_cuota,
       c.dias_mora, c.dias_morosidad, c.observaciones
FROM cuotas c
WHERE c.prestamo_id IN (
  SELECT p.id FROM prestamos p
  WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V25677920')) OR cedula LIKE '%25677920%')
     OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V25677920'))
     OR p.cedula LIKE '%25677920%'
)
ORDER BY c.prestamo_id, c.numero_cuota;

-- =============================================================================
-- 4) PAGOS asociados (por préstamo o por cédula en tabla pagos)
-- =============================================================================
SELECT pg.id AS pago_id, pg.prestamo_id, pg.cedula AS cedula_pago, pg.fecha_pago, pg.monto_pagado,
       pg.referencia_pago, pg.numero_documento, pg.institucion_bancaria, pg.estado AS estado_pago,
       pg.conciliado, pg.fecha_conciliacion, pg.fecha_registro, pg.notas
FROM pagos pg
WHERE pg.prestamo_id IN (
  SELECT p.id FROM prestamos p
  WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V25677920')) OR cedula LIKE '%25677920%')
     OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V25677920'))
     OR p.cedula LIKE '%25677920%'
)
   OR TRIM(UPPER(pg.cedula)) = TRIM(UPPER('V25677920'))
   OR pg.cedula LIKE '%25677920%'
ORDER BY pg.fecha_pago;

-- =============================================================================
-- 5) APLICACIÓN PAGO → CUOTA (cuota_pagos): qué pago se aplicó a qué cuota
-- =============================================================================
SELECT cp.id, cp.cuota_id, cp.pago_id, cp.monto_aplicado, cp.fecha_aplicacion, cp.es_pago_completo,
       c.prestamo_id, c.numero_cuota, pg.fecha_pago, pg.monto_pagado, pg.cedula AS cedula_pago
FROM cuota_pagos cp
JOIN cuotas c ON c.id = cp.cuota_id
JOIN pagos pg ON pg.id = cp.pago_id
WHERE c.prestamo_id IN (
  SELECT p.id FROM prestamos p
  WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V25677920')) OR cedula LIKE '%25677920%')
     OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V25677920'))
     OR p.cedula LIKE '%25677920%'
)
ORDER BY cp.pago_id, cp.cuota_id;

-- =============================================================================
-- 6) REVISIÓN MANUAL de esos préstamos (si existe)
-- =============================================================================
SELECT r.prestamo_id, r.estado_revision, r.prestamo_editado, r.actualizado_en, r.creado_en
FROM revision_manual_prestamos r
WHERE r.prestamo_id IN (
  SELECT p.id FROM prestamos p
  WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V25677920')) OR cedula LIKE '%25677920%')
     OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V25677920'))
     OR p.cedula LIKE '%25677920%'
);

-- =============================================================================
-- 7) RESUMEN NUMÉRICO POR PRÉSTAMO (cuotas, pagos, total pagado)
-- =============================================================================
SELECT p.id AS prestamo_id, p.estado, p.total_financiamiento, p.numero_cuotas,
       (SELECT COUNT(*) FROM cuotas c WHERE c.prestamo_id = p.id) AS total_cuotas,
       (SELECT COUNT(*) FROM cuotas c WHERE c.prestamo_id = p.id AND c.fecha_pago IS NOT NULL) AS cuotas_pagadas,
       (SELECT COALESCE(SUM(pg.monto_pagado), 0) FROM pagos pg WHERE pg.prestamo_id = p.id) AS total_pagado_prestamo
FROM prestamos p
WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V25677920')) OR cedula LIKE '%25677920%')
   OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V25677920'))
   OR p.cedula LIKE '%25677920%'
ORDER BY p.id;

-- =============================================================================
-- 8) COHERENCIA FECHAS: aprobación vs requerimiento (por si aplica)
-- =============================================================================
SELECT p.id, p.cedula, p.fecha_requerimiento, p.fecha_aprobacion::date AS fecha_aprobacion,
       CASE
         WHEN p.fecha_aprobacion IS NOT NULL AND p.fecha_requerimiento > (p.fecha_aprobacion)::date
         THEN 'INCOHERENTE (aprobación < requerimiento)'
         ELSE 'OK'
       END AS coherencia
FROM prestamos p
WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V25677920')) OR cedula LIKE '%25677920%')
   OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V25677920'))
   OR p.cedula LIKE '%25677920%';

-- =============================================================================
-- 9) AUDITORÍA reciente (si existe tabla auditoria y tiene referencia a préstamo/cliente)
-- =============================================================================
-- Descomentar si tu tabla auditoria tiene entidad_id o similar para préstamos:
/*
SELECT a.id, a.entidad, a.entidad_id, a.accion, a.detalle, a.usuario_id, a.fecha
FROM auditoria a
WHERE a.entidad = 'prestamo'
  AND a.entidad_id::int IN (
    SELECT p.id FROM prestamos p
    WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V25677920')) OR cedula LIKE '%25677920%')
       OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V25677920'))
  )
ORDER BY a.fecha DESC
LIMIT 50;
*/
