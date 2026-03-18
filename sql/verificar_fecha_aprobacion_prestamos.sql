-- =============================================================================
-- Verificación: fecha_aprobacion en préstamos y uso en tabla de amortización
-- Ejecutar contra la BD de RAPICREDIT (PostgreSQL).
-- =============================================================================

-- 1) Resumen: cuántos préstamos tienen / no tienen fecha_aprobacion
SELECT
  COUNT(*) FILTER (WHERE fecha_aprobacion IS NOT NULL) AS con_fecha_aprobacion,
  COUNT(*) FILTER (WHERE fecha_aprobacion IS NULL)     AS sin_fecha_aprobacion,
  COUNT(*)                                             AS total
FROM prestamos;

-- 2) Préstamos SIN fecha_aprobacion (listado para revisión)
SELECT id, cliente_id, estado, fecha_registro::date, fecha_requerimiento, fecha_base_calculo, total_financiamiento, numero_cuotas
FROM prestamos
WHERE fecha_aprobacion IS NULL
ORDER BY id;

-- 3) Préstamos APROBADOS sin fecha_aprobacion (inconsistencia: deberían tener fecha)
SELECT id, cliente_id, estado, fecha_registro::date, fecha_requerimiento, fecha_base_calculo, total_financiamiento
FROM prestamos
WHERE UPPER(TRIM(estado)) = 'APROBADO'
  AND fecha_aprobacion IS NULL
ORDER BY id;

-- 4) Préstamos que tienen cuotas pero no tienen fecha_aprobacion (la tabla de amortización pudo generarse con hoy/fecha_requerimiento)
SELECT p.id, p.estado, p.fecha_registro::date, p.fecha_requerimiento, p.fecha_base_calculo,
       (SELECT COUNT(*) FROM cuotas c WHERE c.prestamo_id = p.id) AS num_cuotas,
       (SELECT MIN(c.fecha_vencimiento) FROM cuotas c WHERE c.prestamo_id = p.id) AS primera_cuota_vencimiento
FROM prestamos p
WHERE p.fecha_aprobacion IS NULL
  AND EXISTS (SELECT 1 FROM cuotas c WHERE c.prestamo_id = p.id)
ORDER BY p.id;

-- 5) Coherencia: préstamos APROBADOS con cuotas — primera cuota debería ser coherente con fecha_aprobacion o fecha_base_calculo
--    (fecha_vencimiento cuota 1 ≈ fecha_base + 1 periodo según modalidad)
SELECT p.id,
       p.estado,
       p.fecha_aprobacion::date     AS fecha_aprobacion,
       p.fecha_base_calculo         AS fecha_base_calculo,
       p.modalidad_pago,
       c1.fecha_vencimiento         AS primera_cuota_vencimiento
FROM prestamos p
JOIN LATERAL (
  SELECT fecha_vencimiento
  FROM cuotas
  WHERE prestamo_id = p.id
  ORDER BY numero_cuota
  LIMIT 1
) c1 ON true
WHERE p.fecha_aprobacion IS NOT NULL
  AND EXISTS (SELECT 1 FROM cuotas c WHERE c.prestamo_id = p.id)
ORDER BY p.id;

-- 6) Conteo por estado: cuántos tienen fecha_aprobacion por estado
SELECT estado,
       COUNT(*) AS total,
       COUNT(fecha_aprobacion) AS con_fecha_aprobacion,
       COUNT(*) - COUNT(fecha_aprobacion) AS sin_fecha_aprobacion
FROM prestamos
GROUP BY estado
ORDER BY estado;
