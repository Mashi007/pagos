-- =============================================================================
-- MARCAR TODOS LOS PAGOS COMO CONCILIADOS
-- =============================================================================
-- Aviso: haga backup de la tabla pagos antes de ejecutar el UPDATE.
-- Este script actualiza: conciliado, fecha_conciliacion, verificado_concordancia, estado.
-- =============================================================================

-- 1) Ver cuántos quedarían afectados (aún no conciliados)
SELECT COUNT(*) AS pagos_sin_conciliar
  FROM pagos
 WHERE conciliado IS NOT TRUE
    OR conciliado IS NULL;

-- 2) UPDATE: marcar todos como conciliados
UPDATE pagos
   SET conciliado       = true,
       fecha_conciliacion = COALESCE(fecha_conciliacion, CURRENT_TIMESTAMP),
       verificado_concordancia = 'SI',
       estado            = COALESCE(NULLIF(TRIM(estado), ''), 'PAGADO')
 WHERE conciliado IS NOT TRUE
    OR conciliado IS NULL;

-- 3) Comprobar: no debe quedar ninguno sin conciliar
SELECT COUNT(*) AS sin_conciliar_debe_ser_0
  FROM pagos
 WHERE conciliado IS NOT TRUE
    OR conciliado IS NULL;
