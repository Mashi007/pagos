-- Tasas BCV / oficiales por fecha (Bs por USD). Origen: carga manual usuario.
-- Tabla: tasas_cambio_diaria (fecha UNIQUE, tasa_oficial NUMERIC).
-- Si la fecha ya existe, actualiza tasa_oficial y updated_at.

BEGIN;

INSERT INTO tasas_cambio_diaria (fecha, tasa_oficial, usuario_email)
VALUES
  ('2025-12-03'::date, 271.4::numeric, 'manual_bcv'),
  ('2025-12-05'::date, 276.25::numeric, 'manual_bcv'),
  ('2026-02-11'::date, 425.1::numeric, 'manual_bcv'),
  ('2026-02-25'::date, 440.8::numeric, 'manual_bcv'),
  ('2026-03-01'::date, 448.5::numeric, 'manual_bcv'),
  ('2026-03-05'::date, 455.95::numeric, 'manual_bcv'),
  ('2026-03-07'::date, 460.05::numeric, 'manual_bcv'),
  ('2026-03-08'::date, 460.05::numeric, 'manual_bcv'),
  ('2026-03-11'::date, 468.15::numeric, 'manual_bcv')
ON CONFLICT (fecha) DO UPDATE SET
  tasa_oficial = EXCLUDED.tasa_oficial,
  usuario_email = COALESCE(EXCLUDED.usuario_email, tasas_cambio_diaria.usuario_email),
  updated_at = NOW();

COMMIT;
