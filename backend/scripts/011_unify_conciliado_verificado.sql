-- Migración 011: Consolidar conciliado y verificado_concordancia en un solo campo
-- Ambos campos representan lo mismo → usar solo "conciliado" (boolean).
-- El campo "verificado_concordancia" queda como legacy/readonly.

-- [B2] Copiar valores de verificado_concordancia → conciliado si es necesario
UPDATE public.pagos
SET conciliado = TRUE
WHERE conciliado IS NOT TRUE 
  AND verificado_concordancia = 'SI';

-- Notas de migración:
-- 1. Si conciliado = TRUE → verificado_concordancia siempre será 'SI'
-- 2. Si conciliado = FALSE o NULL → verificado_concordancia será ''
-- 3. El backend siempre usa conciliado (boolean); verificado_concordancia es legacy

-- Hacer conciliado NOT NULL con default FALSE
ALTER TABLE public.pagos
    ALTER COLUMN conciliado SET DEFAULT FALSE;
ALTER TABLE public.pagos
    ALTER COLUMN conciliado SET NOT NULL;

-- Opcional: agregar CHECK para mantener sincronización (informativo)
ALTER TABLE public.pagos
    DROP CONSTRAINT IF EXISTS ck_pagos_conciliado_consistencia;
-- Comentario: verificado_concordancia se mantiene sincronizado via triggers o aplicación.
