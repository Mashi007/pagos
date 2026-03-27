-- Misma logica que GET /api/v1/reportes/exportar/morosidad-cedulas:
-- solo cuotas con cuotas.estado = 'MORA', cliente ACTIVO, prestamo APROBADO.
-- Una fila por cedula: cantidad y suma de monto_cuota.

SELECT
  cl.cedula,
  string_agg(DISTINCT p.modalidad_pago, ', ' ORDER BY p.modalidad_pago) AS modalidad,
  COUNT(c.id) AS cantidad_cuotas,
  COALESCE(SUM(c.monto_cuota), 0) AS total_usd
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
JOIN clientes cl ON p.cliente_id = cl.id
WHERE cl.estado = 'ACTIVO'
  AND p.estado = 'APROBADO'
  AND c.estado = 'MORA'
GROUP BY cl.id, cl.cedula
ORDER BY cl.cedula;
