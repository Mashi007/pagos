-- Total global: todas las cuotas cuyo estado NO es MORA (cliente ACTIVO, prestamo APROBADO).
-- Incluye PAGADO, PAGO_ADELANTADO, PENDIENTE, PARCIAL, VENCIDO, etc.

SELECT
  COUNT(*) AS cantidad_cuotas,
  COALESCE(SUM(c.monto_cuota), 0) AS total_usd
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
JOIN clientes cl ON p.cliente_id = cl.id
WHERE cl.estado = 'ACTIVO'
  AND p.estado = 'APROBADO'
  AND c.estado IS DISTINCT FROM 'MORA';
