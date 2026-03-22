-- =============================================================================
-- Registrar tasas oficiales (Bs. por 1 USD) por fecha de pago — backfill manual
-- =============================================================================
-- 1) Ejecute listar_fechas_sin_tasa_pagos_bs.sql para ver qué fechas faltan.
-- 2) Sustituya fechas y tasas reales (oficial del día del pago).
-- 3) Ajuste usuario_email si desea auditoría.
-- PostgreSQL: ON CONFLICT por UNIQUE(fecha).
-- =============================================================================

-- Sustituya cada tasa_oficial por el valor oficial Bs./USD de ESE día.
INSERT INTO tasas_cambio_diaria (fecha, tasa_oficial, usuario_email)
VALUES
    ('2026-02-20', 3105.75, 'backfill-manual'),
    ('2026-03-12', 3105.75, 'backfill-manual'),
    ('2026-03-14', 3105.75, 'backfill-manual'),
    ('2026-03-16', 3105.75, 'backfill-manual'),
    ('2026-03-17', 3105.75, 'backfill-manual'),
    ('2026-03-18', 3105.75, 'backfill-manual'),
    ('2026-03-19', 3105.75, 'backfill-manual'),
    ('2026-03-20', 3105.75, 'backfill-manual')
ON CONFLICT (fecha) DO UPDATE SET
    tasa_oficial = EXCLUDED.tasa_oficial,
    usuario_email = EXCLUDED.usuario_email,
    updated_at = NOW();
