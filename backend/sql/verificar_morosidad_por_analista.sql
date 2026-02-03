-- =============================================================================
-- Verificación: Morosidad por Analista (gráfico "Cuotas vencidas por analista")
-- Ejecutar en DBeaver contra la misma BD que usa la app.
-- =============================================================================
-- Lógica: cuotas donde HOY > fecha_vencimiento y no están pagadas (fecha_pago IS NULL).
-- El analista sale del préstamo de cada cuota: cuotas.prestamo_id → prestamos.id → prestamos.analista.
-- =============================================================================

-- 1) Resumen por analista (equivale a lo que devuelve GET /api/v1/dashboard/morosidad-por-analista)
SELECT
    COALESCE(p.analista, 'Sin analista') AS analista,
    COUNT(*) AS cantidad_cuotas_vencidas,
    ROUND(SUM(c.monto_cuota)::numeric, 2) AS monto_vencido
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_pago IS NULL
  AND c.fecha_vencimiento < CURRENT_DATE
GROUP BY COALESCE(p.analista, 'Sin analista')
ORDER BY monto_vencido DESC;


-- 2) Detalle: cuotas vencidas con cédula (cliente) y analista (para cruzar)
SELECT
    cl.cedula AS cedula_cliente,
    p.analista,
    c.id AS cuota_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.fecha_pago
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
LEFT JOIN clientes cl ON c.cliente_id = cl.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_pago IS NULL
  AND c.fecha_vencimiento < CURRENT_DATE
ORDER BY p.analista, cl.cedula, c.fecha_vencimiento;


-- 3) Total de cuotas vencidas (debe coincidir con la suma de cantidad_cuotas_vencidas del query 1)
SELECT COUNT(*) AS total_cuotas_vencidas
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_pago IS NULL
  AND c.fecha_vencimiento < CURRENT_DATE;


-- Nota: Si tu tabla cuotas usa "monto" en lugar de "monto_cuota", cambia c.monto_cuota por c.monto en los SELECT.
