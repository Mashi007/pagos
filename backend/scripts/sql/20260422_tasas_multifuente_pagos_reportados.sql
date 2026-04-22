-- Ejecutar en PostgreSQL (Render) antes de desplegar código que usa las columnas.
-- La primera y última SELECT sirven para registrar inicio/fin (p. ej. copiar a tu tabla de ejecución).

SELECT clock_timestamp() AS start_time;

--
-- Semántica tras la migración:
--   - Toda tasa ya guardada en `tasa_oficial` (histórica y vigente) ES la tasa **Euro**
--     (Bs. por 1 USD). No se alteran valores: solo se documenta y se añaden columnas nuevas.
--   - `tasa_bcv` y `tasa_binance` quedan NULL hasta que administración cargue esas fuentes
--     por fecha (el cliente solo podrá elegir BCV/Binance cuando existan filas con valor).

ALTER TABLE tasas_cambio_diaria
  ADD COLUMN IF NOT EXISTS tasa_bcv NUMERIC(15, 6),
  ADD COLUMN IF NOT EXISTS tasa_binance NUMERIC(15, 6);

COMMENT ON COLUMN tasas_cambio_diaria.tasa_oficial IS
  'Euro: Bs por 1 USD. Tasas vigentes e históricas legadas viven aquí; sin cambio de dato en esta migración.';

COMMENT ON COLUMN tasas_cambio_diaria.tasa_bcv IS
  'BCV oficial: Bs por 1 USD. NULL si no cargada para esa fecha.';

COMMENT ON COLUMN tasas_cambio_diaria.tasa_binance IS
  'Binance P2P: Bs por 1 USD. NULL si no cargada para esa fecha.';

ALTER TABLE pagos_reportados
  ADD COLUMN IF NOT EXISTS fuente_tasa_cambio VARCHAR(16) DEFAULT 'euro';

UPDATE pagos_reportados SET fuente_tasa_cambio = 'euro' WHERE fuente_tasa_cambio IS NULL;

COMMENT ON COLUMN pagos_reportados.fuente_tasa_cambio IS
  'bcv | euro | binance — fuente usada al reportar en Bs; histórico sin columna = euro (tasa_oficial del día).';

SELECT clock_timestamp() AS finish_time;
