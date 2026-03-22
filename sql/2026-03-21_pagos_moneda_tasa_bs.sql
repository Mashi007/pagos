-- Pagos: auditoria moneda / tasa Bs->USD (fecha de pago = clave en tasas_cambio_diaria)
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS moneda_registro VARCHAR(10);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS monto_bs_original NUMERIC(15, 2);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS tasa_cambio_bs_usd NUMERIC(15, 6);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS fecha_tasa_referencia DATE;
COMMENT ON COLUMN pagos.monto_pagado IS 'Monto en USD para cartera; si moneda_registro=BS, convertido con tasa del dia fecha_tasa_referencia.';
