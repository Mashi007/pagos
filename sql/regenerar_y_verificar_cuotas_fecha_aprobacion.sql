-- =============================================================================
-- Regenerar cuotas según fecha_aprobacion + modalidad_pago (alineado con backend:
--   backend/app/api/v1/endpoints/prestamos.py → _generar_cuotas_amortizacion)
--
-- POLÍTICA ACTUAL (producto)
-- -------------------------
-- Tasa de interés por defecto: 0 % anual. Si no se informa otra tasa, el plan es
-- de cuotas iguales (capital / número de cuotas), sin sistema francés. La columna
-- prestamos.tasa_interes en BD tiene default 0.00 acorde a esto.
--
-- ADVERTENCIAS IMPORTANTES
-- ------------------------
-- 1) Borrar cuotas elimina en cascada filas en cuota_pagos (FK on delete CASCADE).
--    Los pagos en tabla "pagos" siguen existiendo, pero pierden la trazabilidad
--    hasta que vuelvas a aplicarlos (p. ej. POST /api/v1/prestamos/conciliar-amortizacion-masiva).
-- 2) Hacer BACKUP o snapshot antes de ejecutar la parte destructiva.
-- 3) Préstamos sin fecha_aprobacion o con numero_cuotas < 1 no se regeneran aquí.
-- 4) Si solo quieres probar, usa la CTE "prestamos_objetivo" con un filtro por id.
-- =============================================================================
--
-- =============================================================================
-- PROCEDIMIENTO DE REGENERACIÓN ALINEADO CON Cascada (plan operativo — actualizado)
-- =============================================================================
--
-- Objetivo: reconstruir el plan de cuotas según la fecha de aprobación y la
-- modalidad vigentes, y volver a imputar los cobros ya existentes en orden
-- (primero cuota 1, luego 2, …), sin borrar los registros de pago.
--
-- | Paso | Acción |
-- |------|--------|
-- | **0** | **Análisis integral:** alinear políticas de producto (fechas, tasas por defecto 0 %, Cascada por número de cuota, estados) con lo que muestra y permite el sistema; checklist back/front antes de tocar datos. |
-- | **1** | **Backup:** copia de seguridad de la BD completa o, como mínimo, tablas `cuotas` y `cuota_pagos`, más snapshot de conteos por préstamo/cuota. |
-- | **2** | **Pre-chequeos:** detectar desalineación de la cuota 1 respecto a `fecha_aprobacion` (consultas de este script); verificar integridad `pagos` ↔ `cuota_pagos` (p. ej. `sql/verificar_trazabilidad_pagos_cuotas_prestamos.sql`). |
-- | **3** | **Regenerar cuotas:** `DELETE` del conjunto objetivo en `cuotas` (CASCADE borra `cuota_pagos`); luego `INSERT` del plan nuevo con la misma lógica que el backend (secciones E preview y F). Los `pagos` permanecen en tabla `pagos`. |
-- | **4** | **Re-aplicar pagos:** `POST /api/v1/prestamos/conciliar-amortizacion-masiva` (body opcional `prestamo_ids`) para re-imputar cobros conciliados al nuevo calendario. |
-- | **5** | **Post-chequeo:** repetir trazabilidad y consultas “cuota 1 vs esperado”; revisar casos donde capital, número de cuotas o tasa difieren del histórico con el que se registraron cobros. |
--
-- Lectura financiera (equivalencia): (1) respaldo del estado de cartera y vínculos
-- pago–cuota. (2) auditoría de coherencia fecha de aprobación vs primer vencimiento
-- e integridad de aplicaciones. (3) sustitución del calendario de vencimientos y
-- montos de cuota. (4) redistribución de cobros al nuevo plan en orden de cuotas.
-- (5) cierre de auditoría y cuadre.
--
-- -----------------------------------------------------------------------------
-- Paso 0 — Análisis integral: políticas backend y coherencia con frontend
-- -----------------------------------------------------------------------------
-- Antes de borrar o regenerar datos, validar que el equipo entiende y documenta
-- la misma "fuente de verdad" y los mismos flujos que verá el usuario en pantalla.
--
-- Backend (revisar código y comportamiento real de API)
-- - Amortización: base de fechas = `fecha_aprobacion` (no confundir con otros
--   campos legacy si aún existen en BD); modalidad MENSUAL / QUINCENAL / SEMANAL.
-- - Generación de cuotas: `prestamos.py` → `_generar_cuotas_amortizacion`,
--   `_resolver_monto_cuota` (cuota plana si tasa 0 % por defecto; sistema francés
--   solo si la tasa anual es mayor que cero).
-- - Aplicación de pagos: Cascada por `numero_cuota` ASC; historial en `cuota_pagos`;
--   re-aplicación tras regenerar vía `aplicar_pagos_pendientes_prestamo` /
--   `conciliar-amortizacion-masiva`.
-- - Estados de cuota (PENDIENTE, PAGADO, mora/vencido según reglas actuales) y
--   transición a LIQUIDADO del préstamo cuando todas las cuotas cubiertas.
-- - Endpoints que disparan generación o recálculo (crear/actualizar préstamo,
--   aprobar manual, asignar fecha, carga masiva) para no dejar huecos si el front
--   solo actualiza `fecha_aprobacion` sin pasar por el flujo que regenera cuotas.
--
-- Frontend (coherencia con lo anterior)
-- - Qué campos se muestran y editan (p. ej. solo "fecha de aprobación" vs fechas
--   que ya no deben usarse para amortización); textos y tooltips alineados al back.
-- - Listados y detalle de préstamo/cuotas: mismos criterios de orden y etiquetas
--   que la API (número de cuota, vencimiento, estado, total pagado).
-- - Caché / refetch tras edición (evitar UI con datos viejos tras corregir fechas).
-- - Exportaciones (PDF/Excel amortización) si existen: deben reflejar las mismas
--   fechas y montos que `GET .../cuotas`.
--
-- Entregable sugerido del paso 0: breve checklist firmado (qué políticas aplican,
-- qué pantallas las reflejan, qué endpoints intervienen) antes del paso 1.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- A) Funciones auxiliares (ejecutar una vez; DROP si ya existen y cambias lógica)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_add_months_keep_day(d date, meses int)
RETURNS date
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
  y  int;
  mo int;
  dd int;
  last_day int;
BEGIN
  IF meses IS NULL OR meses <= 0 THEN
    RETURN d;
  END IF;
  y := EXTRACT(YEAR FROM d)::int;
  mo := EXTRACT(MONTH FROM d)::int;
  dd := EXTRACT(DAY FROM d)::int;
  y := y + (mo + meses - 1) / 12;
  mo := (mo + meses - 1) % 12 + 1;
  last_day := EXTRACT(
    DAY FROM (
      (DATE_TRUNC('month', make_date(y, mo, 1)) + INTERVAL '1 month - 1 day')::date
    )
  )::int;
  RETURN make_date(y, mo, LEAST(dd, last_day));
END;
$$;

CREATE OR REPLACE FUNCTION fn_monto_cuota_frances(p_capital numeric, i_periodo numeric, n int)
RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  IF n IS NULL OR n <= 0 THEN
    RETURN 0;
  END IF;
  IF i_periodo IS NULL OR i_periodo <= 0 THEN
    RETURN ROUND(p_capital / n, 2);
  END IF;
  RETURN ROUND(
    p_capital * (i_periodo * POWER(1::numeric + i_periodo, n))
    / (POWER(1::numeric + i_periodo, n) - 1),
    2
  );
END;
$$;

-- -----------------------------------------------------------------------------
-- B) COMPROBAR: desajuste de la cuota 1 respecto a la regla (fecha_aprobacion)
--    MENSUAL   → vencimiento cuota 1 = mismo día del mes, +1 mes (fn_add_months_keep_day)
--    QUINCENAL → fecha_aprobacion::date + (15*1 - 1) días
--    SEMANAL   → fecha_aprobacion::date + (7*1 - 1) días
-- -----------------------------------------------------------------------------

WITH p AS (
  SELECT
    pr.id AS prestamo_id,
    pr.cliente_id,
    UPPER(COALESCE(NULLIF(TRIM(pr.modalidad_pago), ''), 'MENSUAL')) AS modalidad,
    pr.numero_cuotas,
    pr.fecha_aprobacion::date AS fecha_aprob,
    c.numero_cuota,
    c.fecha_vencimiento AS venc_actual,
    c.id AS cuota_id
  FROM prestamos pr
  JOIN cuotas c ON c.prestamo_id = pr.id AND c.numero_cuota = 1
  WHERE pr.fecha_aprobacion IS NOT NULL
    AND pr.numero_cuotas >= 1
)
SELECT
  p.prestamo_id,
  p.modalidad,
  p.fecha_aprob,
  p.venc_actual,
  CASE
    WHEN p.modalidad = 'MENSUAL' THEN fn_add_months_keep_day(p.fecha_aprob, 1)
    WHEN p.modalidad = 'QUINCENAL' THEN (p.fecha_aprob + (15 * 1 - 1) * INTERVAL '1 day')::date
    WHEN p.modalidad = 'SEMANAL' THEN (p.fecha_aprob + (7 * 1 - 1) * INTERVAL '1 day')::date
    ELSE fn_add_months_keep_day(p.fecha_aprob, 1)
  END AS venc_esperado_cuota_1,
  (p.venc_actual IS DISTINCT FROM
    CASE
      WHEN p.modalidad = 'MENSUAL' THEN fn_add_months_keep_day(p.fecha_aprob, 1)
      WHEN p.modalidad = 'QUINCENAL' THEN (p.fecha_aprob + (15 * 1 - 1) * INTERVAL '1 day')::date
      WHEN p.modalidad = 'SEMANAL' THEN (p.fecha_aprob + (7 * 1 - 1) * INTERVAL '1 day')::date
      ELSE fn_add_months_keep_day(p.fecha_aprob, 1)
    END
  ) AS desajuste
FROM p
WHERE p.venc_actual IS DISTINCT FROM
  CASE
    WHEN p.modalidad = 'MENSUAL' THEN fn_add_months_keep_day(p.fecha_aprob, 1)
    WHEN p.modalidad = 'QUINCENAL' THEN (p.fecha_aprob + (15 * 1 - 1) * INTERVAL '1 day')::date
    WHEN p.modalidad = 'SEMANAL' THEN (p.fecha_aprob + (7 * 1 - 1) * INTERVAL '1 day')::date
    ELSE fn_add_months_keep_day(p.fecha_aprob, 1)
  END
ORDER BY p.prestamo_id;

-- Resumen de cuántos préstamos tienen la cuota 1 mal alineada:
-- SELECT COUNT(*) FROM ( <consulta anterior sin ORDER BY> ) sub;


-- -----------------------------------------------------------------------------
-- C) COMPROBAR: préstamos con fecha_aprobacion pero sin cuotas (o distinto N)
-- -----------------------------------------------------------------------------

SELECT
  pr.id AS prestamo_id,
  pr.numero_cuotas AS n_declarado,
  COUNT(c.id) AS n_cuotas_en_tabla
FROM prestamos pr
LEFT JOIN cuotas c ON c.prestamo_id = pr.id
WHERE pr.fecha_aprobacion IS NOT NULL
  AND pr.numero_cuotas >= 1
GROUP BY pr.id, pr.numero_cuotas
HAVING COUNT(c.id) <> pr.numero_cuotas
ORDER BY pr.id;


-- -----------------------------------------------------------------------------
-- D) COMPROBAR: préstamos que NO se pueden regenerar con este script (sin fecha)
-- -----------------------------------------------------------------------------

SELECT id, estado, numero_cuotas
FROM prestamos
WHERE fecha_aprobacion IS NULL
  AND EXISTS (SELECT 1 FROM cuotas c WHERE c.prestamo_id = prestamos.id)
ORDER BY id;


-- -----------------------------------------------------------------------------
-- E) PREVIEW: filas que se insertarían (primeros 500 registros; ajustar JOIN)
--     Copia la CTE "prestamos_objetivo" de la sección F y úsala aquí si filtras por ids.
-- -----------------------------------------------------------------------------

WITH prestamos_objetivo AS (
  SELECT *
  FROM prestamos pr
  WHERE pr.fecha_aprobacion IS NOT NULL
    AND pr.numero_cuotas >= 1
  -- AND pr.id IN (208, 209)  -- descomentar para prueba acotada
),
base AS (
  SELECT
    pr.id AS prestamo_id,
    pr.cliente_id,
    UPPER(COALESCE(NULLIF(TRIM(pr.modalidad_pago), ''), 'MENSUAL')) AS modalidad,
    pr.numero_cuotas AS n,
    pr.fecha_aprobacion::date AS fecha_base,
    pr.total_financiamiento::numeric AS capital,
    COALESCE(pr.tasa_interes, 0)::numeric AS tasa_anual
  FROM prestamos_objetivo pr
),
mc AS (
  SELECT
    b.*,
    CASE b.modalidad
      WHEN 'MENSUAL' THEN 12
      WHEN 'QUINCENAL' THEN 24
      WHEN 'SEMANAL' THEN 52
      ELSE 12
    END AS periodos_anio,
    CASE
      WHEN COALESCE(b.tasa_anual, 0) <= 0 OR b.n <= 0 THEN ROUND(b.capital / NULLIF(b.n, 0), 2)
      ELSE fn_monto_cuota_frances(
        b.capital,
        ((b.tasa_anual / 100) / NULLIF(
          CASE b.modalidad
            WHEN 'MENSUAL' THEN 12
            WHEN 'QUINCENAL' THEN 24
            WHEN 'SEMANAL' THEN 52
            ELSE 12
          END,
          0
        ))::numeric,
        b.n
      )
    END AS monto_cuota
  FROM base b
),
filas AS (
  SELECT
    mc.prestamo_id,
    mc.cliente_id,
    gs.n::int AS numero_cuota,
    CASE
      WHEN mc.modalidad = 'MENSUAL' THEN fn_add_months_keep_day(mc.fecha_base, gs.n::int)
      WHEN mc.modalidad = 'QUINCENAL' THEN (mc.fecha_base + (15 * gs.n::int - 1) * INTERVAL '1 day')::date
      WHEN mc.modalidad = 'SEMANAL' THEN (mc.fecha_base + (7 * gs.n::int - 1) * INTERVAL '1 day')::date
      ELSE fn_add_months_keep_day(mc.fecha_base, gs.n::int)
    END AS fecha_vencimiento,
    mc.monto_cuota,
    ROUND(mc.monto_cuota * mc.n, 2) AS total_plan,
    ROUND(mc.monto_cuota * mc.n - (gs.n::int - 1) * mc.monto_cuota, 2) AS saldo_capital_inicial,
    GREATEST(ROUND(mc.monto_cuota * mc.n - gs.n::int * mc.monto_cuota, 2), 0) AS saldo_capital_final
  FROM mc
  CROSS JOIN LATERAL generate_series(1, mc.n) AS gs(n)
)
SELECT
  prestamo_id,
  cliente_id,
  numero_cuota,
  fecha_vencimiento,
  monto_cuota AS monto_cuota_col,
  saldo_capital_inicial,
  saldo_capital_final,
  ROUND(saldo_capital_inicial - saldo_capital_final, 2) AS monto_capital,
  ROUND(monto_cuota - (saldo_capital_inicial - saldo_capital_final), 2) AS monto_interes
FROM filas
ORDER BY prestamo_id, numero_cuota
LIMIT 500;


-- =============================================================================
-- F) REGENERACIÓN MASIVA (DESTRUCTIVA)
-- =============================================================================
-- Ejecutar en una transacción. Orden: borrar cuotas (CASCADE borra cuota_pagos).
-- Después, en la app: POST /api/v1/prestamos/conciliar-amortizacion-masiva
-- para volver a aplicar pagos conciliados a las nuevas cuotas.
--
-- BEGIN;
--
-- WITH prestamos_objetivo AS (
--   SELECT pr.id
--   FROM prestamos pr
--   WHERE pr.fecha_aprobacion IS NOT NULL
--     AND pr.numero_cuotas >= 1
--   -- AND NOT EXISTS (
--   --   SELECT 1 FROM cuota_pagos cp
--   --   JOIN cuotas c ON c.id = cp.cuota_id
--   --   WHERE c.prestamo_id = pr.id
--   -- )  -- descomentar si solo quieres préstamos SIN pagos ya aplicados a cuotas
-- )
-- DELETE FROM cuotas c
-- USING prestamos_objetivo t
-- WHERE c.prestamo_id = t.id;
--
-- WITH prestamos_objetivo AS (
--   SELECT *
--   FROM prestamos pr
--   WHERE pr.fecha_aprobacion IS NOT NULL
--     AND pr.numero_cuotas >= 1
-- ),
-- base AS (
--   SELECT
--     pr.id AS prestamo_id,
--     pr.cliente_id,
--     UPPER(COALESCE(NULLIF(TRIM(pr.modalidad_pago), ''), 'MENSUAL')) AS modalidad,
--     pr.numero_cuotas AS n,
--     pr.fecha_aprobacion::date AS fecha_base,
--     pr.total_financiamiento::numeric AS capital,
--     COALESCE(pr.tasa_interes, 0)::numeric AS tasa_anual
--   FROM prestamos_objetivo pr
-- ),
-- mc AS (
--   SELECT
--     b.*,
--     CASE
--       WHEN COALESCE(b.tasa_anual, 0) <= 0 OR b.n <= 0 THEN ROUND(b.capital / NULLIF(b.n, 0), 2)
--       ELSE fn_monto_cuota_frances(
--         b.capital,
--         ((b.tasa_anual / 100) / NULLIF(
--           CASE b.modalidad
--             WHEN 'MENSUAL' THEN 12
--             WHEN 'QUINCENAL' THEN 24
--             WHEN 'SEMANAL' THEN 52
--             ELSE 12
--           END,
--           0
--         ))::numeric,
--         b.n
--       )
--     END AS monto_cuota
--   FROM base b
-- ),
-- filas AS (
--   SELECT
--     mc.prestamo_id,
--     mc.cliente_id,
--     gs.n::int AS numero_cuota,
--     CASE
--       WHEN mc.modalidad = 'MENSUAL' THEN fn_add_months_keep_day(mc.fecha_base, gs.n::int)
--       WHEN mc.modalidad = 'QUINCENAL' THEN (mc.fecha_base + (15 * gs.n::int - 1) * INTERVAL '1 day')::date
--       WHEN mc.modalidad = 'SEMANAL' THEN (mc.fecha_base + (7 * gs.n::int - 1) * INTERVAL '1 day')::date
--       ELSE fn_add_months_keep_day(mc.fecha_base, gs.n::int)
--     END AS fecha_vencimiento,
--     mc.monto_cuota,
--     ROUND(mc.monto_cuota * mc.n, 2) AS total_plan,
--     ROUND(mc.monto_cuota * mc.n - (gs.n::int - 1) * mc.monto_cuota, 2) AS saldo_capital_inicial,
--     GREATEST(ROUND(mc.monto_cuota * mc.n - gs.n::int * mc.monto_cuota, 2), 0) AS saldo_capital_final
--   FROM mc
--   CROSS JOIN LATERAL generate_series(1, mc.n) AS gs(n)
-- )
-- INSERT INTO cuotas (
--   prestamo_id,
--   cliente_id,
--   numero_cuota,
--   fecha_vencimiento,
--   monto_cuota,
--   saldo_capital_inicial,
--   saldo_capital_final,
--   monto_capital,
--   monto_interes,
--   estado,
--   dias_mora,
--   pago_id,
--   total_pagado,
--   fecha_pago,
--   observaciones,
--   es_cuota_especial
-- )
-- SELECT
--   f.prestamo_id,
--   f.cliente_id,
--   f.numero_cuota,
--   f.fecha_vencimiento,
--   f.monto_cuota,
--   f.saldo_capital_inicial,
--   f.saldo_capital_final,
--   ROUND(f.saldo_capital_inicial - f.saldo_capital_final, 2),
--   ROUND(f.monto_cuota - (f.saldo_capital_inicial - f.saldo_capital_final), 2),
--   'PENDIENTE',
--   0,
--   NULL,
--   NULL,
--   NULL,
--   NULL,
--   NULL
-- FROM filas f;
--
-- COMMIT;
-- -- ROLLBACK;  -- si algo no cuadra

-- -----------------------------------------------------------------------------
-- G) POST-VERIFICACIÓN: la consulta de desajuste (sección B) debe devolver 0 filas
-- -----------------------------------------------------------------------------
