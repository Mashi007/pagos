-- ============================================================================
-- FASE 2 PARTE 1: Vistas Materializadas
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS clientes_retrasados_mv CASCADE;

CREATE MATERIALIZED VIEW clientes_retrasados_mv AS
SELECT 
    c.id, 
    c.cedula, 
    COUNT(*) as cuotas_retrasadas,
    SUM(cu.monto_cuota) as monto_total_retrasado,
    MIN(cu.fecha_vencimiento) as fecha_mas_antigua,
    MAX(cu.fecha_vencimiento) as fecha_mas_reciente
FROM clientes c
JOIN prestamos p ON c.id = p.cliente_id
JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE cu.fecha_vencimiento < CURRENT_DATE
  AND cu.estado != 'CANCELADA'
GROUP BY c.id, c.cedula;

CREATE INDEX idx_clientes_retrasados_mv_cedula 
ON clientes_retrasados_mv (cedula);

-- Verificar
SELECT COUNT(*) as total_clientes_retrasados FROM clientes_retrasados_mv;
