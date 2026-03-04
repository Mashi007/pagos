-- Migration: 016_crear_tabla_cuota_pagos.sql
-- Propósito: Crear tabla join cuota_pagos para historial completo de pagos por cuota
-- Razón: Actual pago_id en cuota solo guarda el ÚLTIMO pago; se pierden pagos parciales
-- Solución: cuota_pagos registra TODOS los pagos aplicados a cada cuota con monto y orden FIFO

BEGIN;

-- 1. Crear tabla cuota_pagos
CREATE TABLE IF NOT EXISTS public.cuota_pagos (
    id BIGSERIAL PRIMARY KEY,
    cuota_id INTEGER NOT NULL,
    pago_id INTEGER NOT NULL,
    monto_aplicado NUMERIC(14, 2) NOT NULL,
    fecha_aplicacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    orden_aplicacion INTEGER NOT NULL DEFAULT 0,
    es_pago_completo BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cuota_id) REFERENCES public.cuotas(id) ON DELETE CASCADE,
    FOREIGN KEY (pago_id) REFERENCES public.pagos(id) ON DELETE CASCADE
);

-- 2. Índices para queries comunes
CREATE INDEX IF NOT EXISTS idx_cuota_pagos_cuota_id ON public.cuota_pagos(cuota_id);
CREATE INDEX IF NOT EXISTS idx_cuota_pagos_pago_id ON public.cuota_pagos(pago_id);
CREATE INDEX IF NOT EXISTS idx_cuota_pagos_fecha ON public.cuota_pagos(fecha_aplicacion);

-- 3. Índice único para prevenir duplicados (mismo pago aplicado 2x a misma cuota)
CREATE UNIQUE INDEX IF NOT EXISTS uq_cuota_pagos_cuota_pago ON public.cuota_pagos(cuota_id, pago_id);

-- 4. Migración de datos existentes: Convertir pago_id existentes en cuota_pagos
-- (Solo si hay datos en cuotas con pago_id no NULL)
INSERT INTO public.cuota_pagos (cuota_id, pago_id, monto_aplicado, fecha_aplicacion, es_pago_completo, creado_en)
SELECT 
    c.id as cuota_id,
    c.pago_id,
    c.total_pagado as monto_aplicado,
    COALESCE(c.fecha_pago, CURRENT_TIMESTAMP) as fecha_aplicacion,
    (c.total_pagado >= c.monto_cuota - 0.01) as es_pago_completo,
    COALESCE(c.creado_en, CURRENT_TIMESTAMP) as creado_en
FROM public.cuotas c
WHERE c.pago_id IS NOT NULL
ON CONFLICT (cuota_id, pago_id) DO NOTHING;

COMMIT;
