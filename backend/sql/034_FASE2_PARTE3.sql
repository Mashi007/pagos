-- ============================================================================
-- FASE 2 PARTE 3: Vista KPIs y Cachés
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS pagos_kpis_mv CASCADE;

CREATE MATERIALIZED VIEW pagos_kpis_mv AS
SELECT 
    COUNT(*) as total_pagos,
    COUNT(CASE WHEN estado='PAGADO' THEN 1 END) as pagos_completados,
    ROUND(
        COUNT(CASE WHEN estado='PAGADO' THEN 1 END)::FLOAT / NULLIF(COUNT(*), 0) * 100, 
        2
    ) as porcentaje_pagado,
    SUM(CASE WHEN estado='PAGADO' THEN monto_pagado ELSE 0 END) as monto_total_pagado,
    ROUND(
        AVG(CASE WHEN estado='PAGADO' AND fecha_conciliacion IS NOT NULL 
            THEN EXTRACT(DAY FROM fecha_conciliacion - fecha_pago) 
            ELSE NULL END),
        2
    ) as dias_promedio_conciliacion,
    DATE_TRUNC('day', NOW()) as fecha_snapshot
FROM pagos
WHERE fecha_pago >= CURRENT_DATE - INTERVAL '30 days';

CREATE INDEX idx_pagos_kpis_mv_fecha 
ON pagos_kpis_mv (fecha_snapshot DESC);

-- Verificar
SELECT * FROM pagos_kpis_mv;
