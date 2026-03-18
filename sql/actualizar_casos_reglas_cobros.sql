-- =============================================================================
-- Actualizar registros que apliquen a las reglas del módulo Cobros
-- Reglas: (1) USDT = USD en moneda; (2) Cédula sin ceros a la izquierda
-- Ejecutar contra la BD PostgreSQL (pagos_reportados).
-- Revisar los SELECT antes de ejecutar los UPDATE (opcional: comentar los UPDATE).
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1) CASOS QUE APLICAN: Moneda USDT → normalizar a USD
-- =============================================================================
SELECT id, referencia_interna, tipo_cedula, numero_cedula, monto, moneda AS moneda_actual,
       'USD' AS moneda_nueva
FROM pagos_reportados
WHERE UPPER(TRIM(moneda)) = 'USDT';

-- Actualizar moneda USDT → USD
UPDATE pagos_reportados
SET moneda = 'USD'
WHERE UPPER(TRIM(moneda)) = 'USDT';

-- =============================================================================
-- 2) CASOS QUE APLICAN: numero_cedula con ceros a la izquierda → normalizar
--    (Regla: nunca tomar en cuenta ceros después de la letra; ej. V-015989899 → V15989899)
-- =============================================================================
SELECT id, referencia_interna, tipo_cedula, numero_cedula AS numero_actual,
       TRIM(LEADING '0' FROM numero_cedula) AS numero_normalizado
FROM pagos_reportados
WHERE numero_cedula IS NOT NULL
  AND numero_cedula <> ''
  AND numero_cedula <> TRIM(LEADING '0' FROM numero_cedula)
  AND TRIM(LEADING '0' FROM numero_cedula) <> '';

-- Actualizar numero_cedula: quitar ceros a la izquierda (no vaciar; si todo ceros se deja '0')
UPDATE pagos_reportados
SET numero_cedula = CASE
  WHEN TRIM(LEADING '0' FROM numero_cedula) = '' THEN '0'
  ELSE TRIM(LEADING '0' FROM numero_cedula)
END
WHERE numero_cedula IS NOT NULL
  AND numero_cedula <> ''
  AND numero_cedula <> TRIM(LEADING '0' FROM numero_cedula);

-- =============================================================================
-- 3) CONSULTA INFORMATIVA: Registros con Banco = BINANCE (no se actualiza dato;
--    la regla "ignorar error fecha" se aplica solo en la validación Gemini)
-- =============================================================================
SELECT id, referencia_interna, institucion_financiera, fecha_pago, estado
FROM pagos_reportados
WHERE UPPER(TRIM(institucion_financiera)) = 'BINANCE';

COMMIT;

-- =============================================================================
-- Resumen opcional (ejecutar después del COMMIT)
-- =============================================================================
-- SELECT 'Moneda USD (antes USDT o USD)' AS regla, COUNT(*) AS total FROM pagos_reportados WHERE UPPER(TRIM(moneda)) = 'USD';
-- SELECT 'Cédula sin ceros a la izquierda' AS regla, COUNT(*) AS total FROM pagos_reportados WHERE numero_cedula = TRIM(LEADING '0' FROM numero_cedula) OR numero_cedula IS NULL OR numero_cedula = '';
