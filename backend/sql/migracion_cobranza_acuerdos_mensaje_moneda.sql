-- Campos estructurados por mensaje en bitacora: fecha, mensaje, cantidad, moneda.
-- Ejecutar si ya aplico migracion_cobranzas_modulo.sql con el esquema anterior.

ALTER TABLE cobranza_acuerdos ADD COLUMN IF NOT EXISTS mensaje TEXT;
ALTER TABLE cobranza_acuerdos ADD COLUMN IF NOT EXISTS cantidad NUMERIC(14, 2);
ALTER TABLE cobranza_acuerdos ADD COLUMN IF NOT EXISTS moneda VARCHAR(10) DEFAULT 'USD';

UPDATE cobranza_acuerdos
SET mensaje = COALESCE(mensaje, notas, ''),
    cantidad = COALESCE(cantidad, monto_compromiso),
    moneda = COALESCE(NULLIF(TRIM(moneda), ''), 'USD')
WHERE mensaje IS NULL OR TRIM(mensaje) = '';

ALTER TABLE cobranza_acuerdos ALTER COLUMN mensaje SET NOT NULL;
ALTER TABLE cobranza_acuerdos ALTER COLUMN moneda SET NOT NULL;
ALTER TABLE cobranza_acuerdos ALTER COLUMN moneda SET DEFAULT 'USD';
