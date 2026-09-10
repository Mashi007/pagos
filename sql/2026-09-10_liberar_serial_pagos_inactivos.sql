-- Libera seriales de pagos no operativos (ANULADO/DUPLICADO/etc.) para que
-- ux_pagos_numero_documento_btrim no bloquee reingresar el mismo comprobante.
-- Idempotente. No toca pagos PAGADO/PENDIENTE/conciliados.

UPDATE public.pagos
SET numero_documento = NULL
WHERE numero_documento IS NOT NULL
  AND btrim(numero_documento) <> ''
  AND (
    UPPER(COALESCE(estado, '')) IN (
      'ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO'
    )
    OR UPPER(COALESCE(estado, '')) LIKE '%ANUL%'
    OR UPPER(COALESCE(estado, '')) LIKE '%REVERS%'
  );
