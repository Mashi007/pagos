-- =============================================================================
-- Vínculo pagos ↔ pagos_reportados (ON en consultas de este archivo)
-- -----------------------------------------------------------------------------
-- Además de COB-||referencia_interna y documento = referencia (histórico), las
-- filas nuevas pueden tener pagos.numero_documento = trim(numero_operacion)
-- del reporte (mismo criterio que la app: pago_reportado_documento).
-- =============================================================================
-- Criterio de negocio (actual)
-- -----------------------------------------------------------------------------
-- Un reporte en bolívares (pagos_reportados.moneda = BS) debe reflejarse en
-- tabla pagos así:
--   monto_pagado        = monto en Bs. / tasa oficial del día (USD, cartera/cuotas)
--   moneda_registro     = 'BS'
--   monto_bs_original   = monto reportado en Bs.
--   tasa_cambio_bs_usd  = tasa oficial (Bs. por 1 USD)
--   fecha_tasa_referencia = fecha de pago usada para la tasa
--
-- Bug histórico: al ingresar, el sistema tomaba el número en Bs. y lo sumaba /
-- aplicaba como si fuera USD (ej. 2.000.000 Bs. → monto_pagado = 2000000.00
-- en la columna que debería ser dólares).
--
-- Este script IDENTIFICA filas en `pagos` ligadas a un reporte BS que NO
-- cumplen la regla anterior (aunque vengan de "Aprobar" con COB- o de import
-- con documento = referencia).
--
-- Tras corregir montos en `pagos`, re-articular préstamos afectados
-- (ej. backend/scripts/rearticular_prestamo_fifo.py; reaplicacion en cascada).
--
-- Si el listado "0" devuelve 0 filas pero usted sabe que hay pagos COB-* en BS
-- mal cargados, casi seguro falta tasa del día: use el listado "0a" (LEFT JOIN).
-- =============================================================================

-- -------------------------------------------------------------------------
-- 0a) RECOMENDADO: mismos criterios que "0" pero con LEFT JOIN a la tasa.
--     Así aparecen filas aunque tasas_cambio_diaria no tenga esa fecha
--     (monto_usd_esperado NULL, motivo_sospecha indica falta de tasa).
-- -------------------------------------------------------------------------
WITH base AS (
    SELECT
        p.id AS pago_id,
        p.prestamo_id,
        p.numero_documento,
        pr.id AS reportado_id,
        pr.referencia_interna,
        pr.fecha_pago,
        pr.monto AS monto_bs_reportado,
        p.monto_pagado AS monto_pagado_actual,
        p.moneda_registro,
        p.monto_bs_original,
        tc.tasa_oficial,
        ROUND((pr.monto::numeric / NULLIF(tc.tasa_oficial, 0)), 2) AS monto_usd_esperado,
        (tc.fecha IS NOT NULL) AS tiene_tasa_del_dia
    FROM pagos p
    JOIN pagos_reportados pr
      ON (
            p.numero_documento = ('COB-' || pr.referencia_interna)
         OR TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.referencia_interna)
         OR (
                TRIM(BOTH FROM COALESCE(pr.numero_operacion, '')) <> ''
            AND TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.numero_operacion)
            )
      )
     AND LENGTH(COALESCE(p.numero_documento, '')) <= 100
    LEFT JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
    WHERE UPPER(TRIM(pr.moneda)) = 'BS'
      AND pr.estado IN ('aprobado', 'importado')
)
SELECT
    b.*,
    CASE
        WHEN NOT b.tiene_tasa_del_dia
            THEN 'falta_tasa: cargar tasas_cambio_diaria para fecha_pago del reporte'
        WHEN b.monto_pagado_actual::numeric = b.monto_bs_reportado::numeric
            THEN 'monto_pagado_igual_a_bs (se aplicó como USD sin convertir)'
        WHEN b.monto_bs_original IS NULL OR TRIM(COALESCE(b.moneda_registro, '')) <> 'BS'
            THEN 'sin_auditoria_BS_o_moneda_distinta'
        ELSE 'monto_USD_no_cuadra_con_tasa'
    END AS motivo_sospecha
FROM base b
WHERE NOT (
    TRIM(COALESCE(b.moneda_registro, '')) = 'BS'
    AND b.monto_bs_original IS NOT NULL
    AND b.tiene_tasa_del_dia
    AND b.monto_usd_esperado IS NOT NULL
    AND ABS(b.monto_pagado_actual::numeric - b.monto_usd_esperado) <= 0.02
)
ORDER BY b.pago_id DESC;

-- -------------------------------------------------------------------------
-- 0) Opcional: igual que 0a pero INNER JOIN a tasa (solo si ya existe tasa).
--     Descomentar solo si necesita ese filtro; por defecto use 0a.
-- -------------------------------------------------------------------------
/*
WITH esperado AS (
    SELECT
        p.id AS pago_id,
        p.prestamo_id,
        p.numero_documento,
        pr.id AS reportado_id,
        pr.referencia_interna,
        pr.fecha_pago,
        pr.monto AS monto_bs_reportado,
        p.monto_pagado AS monto_pagado_actual,
        p.moneda_registro,
        p.monto_bs_original,
        tc.tasa_oficial,
        ROUND((pr.monto::numeric / NULLIF(tc.tasa_oficial, 0)), 2) AS monto_usd_esperado
    FROM pagos p
    JOIN pagos_reportados pr
      ON (
            p.numero_documento = ('COB-' || pr.referencia_interna)
         OR TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.referencia_interna)
         OR (
                TRIM(BOTH FROM COALESCE(pr.numero_operacion, '')) <> ''
            AND TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.numero_operacion)
            )
      )
     AND LENGTH(COALESCE(p.numero_documento, '')) <= 100
    JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
    WHERE UPPER(TRIM(pr.moneda)) = 'BS'
      AND pr.estado IN ('aprobado', 'importado')
)
SELECT
    e.*,
    CASE
        WHEN e.monto_pagado_actual::numeric = e.monto_bs_reportado::numeric
            THEN 'monto_pagado_igual_a_bs (se aplicó como USD sin convertir)'
        WHEN e.monto_bs_original IS NULL OR TRIM(COALESCE(e.moneda_registro, '')) <> 'BS'
            THEN 'sin_auditoria_BS_o_moneda_distinta'
        ELSE 'monto_USD_no_cuadra_con_tasa'
    END AS motivo_sospecha
FROM esperado e
WHERE NOT (
    TRIM(COALESCE(e.moneda_registro, '')) = 'BS'
    AND e.monto_bs_original IS NOT NULL
    AND ABS(e.monto_pagado_actual::numeric - e.monto_usd_esperado) <= 0.02
)
ORDER BY e.pago_id DESC;
*/

-- -------------------------------------------------------------------------
-- 0b) Mismo criterio pero SIN exigir tasa (para ver cuántos quedan fuera por
--     falta de tasa del día)
-- -------------------------------------------------------------------------
/*
SELECT
    p.id AS pago_id,
    pr.referencia_interna,
    pr.fecha_pago,
    pr.monto AS monto_bs,
    p.monto_pagado,
    p.moneda_registro,
    p.monto_bs_original,
    tc.tasa_oficial
FROM pagos p
JOIN pagos_reportados pr
  ON (
        p.numero_documento = ('COB-' || pr.referencia_interna)
     OR TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.referencia_interna)
     OR (
            TRIM(BOTH FROM COALESCE(pr.numero_operacion, '')) <> ''
        AND TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.numero_operacion)
        )
  )
LEFT JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
WHERE UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
  AND tc.fecha IS NULL;
*/

-- -------------------------------------------------------------------------
-- 1) UPDATE: aplicar regla actual (solo tras revisar el SELECT 0)
-- -------------------------------------------------------------------------
/*
UPDATE pagos p
SET
    monto_pagado = sub.monto_usd_esperado,
    moneda_registro = 'BS',
    monto_bs_original = sub.monto_bs_reportado,
    tasa_cambio_bs_usd = sub.tasa_oficial,
    fecha_tasa_referencia = sub.fecha_pago
FROM (
    SELECT
        p2.id AS pid,
        pr.monto AS monto_bs_reportado,
        pr.fecha_pago,
        tc.tasa_oficial,
        ROUND((pr.monto::numeric / NULLIF(tc.tasa_oficial, 0)), 2) AS monto_usd_esperado
    FROM pagos p2
    JOIN pagos_reportados pr
      ON (
            p2.numero_documento = ('COB-' || pr.referencia_interna)
         OR TRIM(BOTH FROM p2.numero_documento) = TRIM(BOTH FROM pr.referencia_interna)
         OR (
                TRIM(BOTH FROM COALESCE(pr.numero_operacion, '')) <> ''
            AND TRIM(BOTH FROM p2.numero_documento) = TRIM(BOTH FROM pr.numero_operacion)
            )
      )
    JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
    WHERE UPPER(TRIM(pr.moneda)) = 'BS'
      AND pr.estado IN ('aprobado', 'importado')
) AS sub
WHERE p.id = sub.pid
  AND NOT (
    TRIM(COALESCE(p.moneda_registro, '')) = 'BS'
    AND p.monto_bs_original IS NOT NULL
    AND ABS(p.monto_pagado::numeric - sub.monto_usd_esperado) <= 0.02
  );
*/

-- -------------------------------------------------------------------------
-- Ejemplo real: 4 pagos COB-* con Bs. guardados como monto_pagado (sin tasa en JOIN)
-- Si usd_esperado sale NULL, falta fila en tasas_cambio_diaria para pr.fecha_pago.
-- -------------------------------------------------------------------------

-- E1) Fecha de pago del reporte y si existe tasa ese día
/*
SELECT
    pr.referencia_interna,
    pr.fecha_pago,
    tc.tasa_oficial,
    ROUND((pr.monto::numeric / NULLIF(tc.tasa_oficial, 0)), 2) AS usd_esperado
FROM pagos_reportados pr
LEFT JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
WHERE pr.referencia_interna IN (
    'RPC-20260316-00007',
    'RPC-20260316-00021',
    'RPC-20260316-00030',
    'RPC-20260318-00053'
);
*/

-- E2) Corregir solo esos pagos (ejecutar SOLO si E1 muestra tasa_oficial en todas las filas)
--     Luego re-articular cada prestamo_id afectado (Cascada).
/*
UPDATE pagos p
SET
    monto_pagado = ROUND((pr.monto::numeric / NULLIF(tc.tasa_oficial, 0)), 2),
    moneda_registro = 'BS',
    monto_bs_original = pr.monto,
    tasa_cambio_bs_usd = tc.tasa_oficial,
    fecha_tasa_referencia = pr.fecha_pago
FROM pagos_reportados pr
JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
WHERE p.numero_documento = ('COB-' || pr.referencia_interna)
  AND p.id IN (57513, 57516, 57519, 57537)
  AND UPPER(TRIM(pr.moneda)) = 'BS';
*/

-- -------------------------------------------------------------------------
-- Paso 1 — Fechas sin tasa: ejecutar listar_fechas_sin_tasa_pagos_bs.sql
-- (misma lógica, salida con cantidad de reportes por fecha).
-- -------------------------------------------------------------------------

-- -------------------------------------------------------------------------
-- DUPLICADOS: mismo reporte BS enlazado a MÁS DE UN pago (ej. RPC-… y COB-RPC-…)
-- Corregir montos en ambos sin resolver duplicado = doble aplicación a cartera.
-- Decidir cuál fila conservar y anular/eliminar la otra (y re-articular una vez).
-- -------------------------------------------------------------------------
/*
SELECT
    pr.referencia_interna,
    pr.id AS reportado_id,
    COUNT(p.id) AS cantidad_pagos,
    STRING_AGG(p.id::text || '=' || p.numero_documento, ' | ' ORDER BY p.id) AS pagos
FROM pagos_reportados pr
JOIN pagos p
  ON (
        p.numero_documento = ('COB-' || pr.referencia_interna)
     OR TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.referencia_interna)
     OR (
            TRIM(BOTH FROM COALESCE(pr.numero_operacion, '')) <> ''
        AND TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.numero_operacion)
        )
  )
WHERE UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
GROUP BY pr.referencia_interna, pr.id
HAVING COUNT(p.id) > 1;
*/

-- -------------------------------------------------------------------------
-- Duplicado RPC- vs COB-RPC: ejecutar backend/sql/eliminar_pagos_duplicados_rpc_vs_cob.sql
-- -------------------------------------------------------------------------

-- -------------------------------------------------------------------------
-- UPDATE masivo (tras cargar TODAS las tasas y resolver duplicados): ambos formatos de documento
-- -------------------------------------------------------------------------
/*
UPDATE pagos p
SET
    monto_pagado = ROUND((pr.monto::numeric / NULLIF(tc.tasa_oficial, 0)), 2),
    moneda_registro = 'BS',
    monto_bs_original = pr.monto,
    tasa_cambio_bs_usd = tc.tasa_oficial,
    fecha_tasa_referencia = pr.fecha_pago
FROM pagos_reportados pr
JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
WHERE UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
  AND (
        p.numero_documento = ('COB-' || pr.referencia_interna)
     OR TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.referencia_interna)
     OR (
            TRIM(BOTH FROM COALESCE(pr.numero_operacion, '')) <> ''
        AND TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.numero_operacion)
        )
  );
*/

-- -------------------------------------------------------------------------
-- DIAGNÓSTICO rápido
-- -------------------------------------------------------------------------
-- Reportes BS por estado:
-- SELECT estado, COUNT(*) FROM pagos_reportados WHERE UPPER(TRIM(moneda)) = 'BS' GROUP BY estado;
