-- =============================================================================
-- Quitar unicidad global de pagos.numero_documento.
-- La regla operativa de no duplicar el mismo pago sigue siendo la huella funcional
-- (prestamo_id, fecha de pago, monto, ref_norm) e indice ux_pagos_fingerprint_activos.
-- Ejecutar en produccion tras desplegar el codigo que ya no exige documento unico.
-- =============================================================================

ALTER TABLE public.pagos
  DROP CONSTRAINT IF EXISTS uq_pagos_numero_documento;
