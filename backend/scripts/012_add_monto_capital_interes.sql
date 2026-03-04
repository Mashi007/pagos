-- Migración 012: Agregar columnas monto_capital y monto_interes a cuotas
-- [B3] Almacenar desglose de capital e interés para evitar derivar en el frontend.

-- 1. Agregar columnas
ALTER TABLE public.cuotas
    ADD COLUMN IF NOT EXISTS monto_capital NUMERIC(14, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS monto_interes NUMERIC(14, 2) DEFAULT 0;

-- 2. Calcular valores iniciales (en caso de cuotas existentes)
-- Capital = saldo_inicial - saldo_final
-- Interés = monto_cuota - capital
UPDATE public.cuotas
SET 
    monto_capital = (saldo_capital_inicial - saldo_capital_final),
    monto_interes = (monto_cuota - (saldo_capital_inicial - saldo_capital_final))
WHERE monto_capital = 0 AND monto_interes = 0;

-- 3. Agregar CHECK para consistencia (monto_capital + monto_interes = monto_cuota ± 0.01)
ALTER TABLE public.cuotas
    DROP CONSTRAINT IF EXISTS ck_cuotas_desglose_consistencia;
ALTER TABLE public.cuotas
    ADD CONSTRAINT ck_cuotas_desglose_consistencia
    CHECK (ABS((monto_capital + monto_interes) - monto_cuota) <= 0.01);
