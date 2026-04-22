-- Fuente de tasa por cédula en lista Bs (Cobros / Infopagos). Valores: bcv | euro | binance (default euro).
ALTER TABLE cedulas_reportar_bs
  ADD COLUMN IF NOT EXISTS fuente_tasa_cambio VARCHAR(16) NOT NULL DEFAULT 'euro';

COMMENT ON COLUMN cedulas_reportar_bs.fuente_tasa_cambio IS
  'Fuente de tasa por defecto si la cédula puede reportar en Bs: bcv | euro | binance.';
