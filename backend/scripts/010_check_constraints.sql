-- Migración 010: Agregar CHECK constraints en pagos y cuotas
-- Refuerza validaciones de datos a nivel BD para garantizar integridad.

-- 1. CHECK en pagos.monto_pagado > 0
ALTER TABLE public.pagos
    DROP CONSTRAINT IF EXISTS ck_pagos_monto_positivo;
ALTER TABLE public.pagos
    ADD CONSTRAINT ck_pagos_monto_positivo 
    CHECK (monto_pagado > 0);

-- 2. CHECK en pagos.estado (valores permitidos)
ALTER TABLE public.pagos
    DROP CONSTRAINT IF EXISTS ck_pagos_estado_valido;
ALTER TABLE public.pagos
    ADD CONSTRAINT ck_pagos_estado_valido
    CHECK (estado IS NULL OR estado IN ('PENDIENTE', 'PAGADO'));

-- 3. CHECK en cuotas.monto_cuota > 0
ALTER TABLE public.cuotas
    DROP CONSTRAINT IF EXISTS ck_cuotas_monto_positivo;
ALTER TABLE public.cuotas
    ADD CONSTRAINT ck_cuotas_monto_positivo
    CHECK (monto_cuota > 0);

-- 4. CHECK en cuotas.estado (valores permitidos)
ALTER TABLE public.cuotas
    DROP CONSTRAINT IF EXISTS ck_cuotas_estado_valido;
ALTER TABLE public.cuotas
    ADD CONSTRAINT ck_cuotas_estado_valido
    CHECK (estado IN ('PENDIENTE', 'PAGADO', 'PAGO_ADELANTADO'));

-- 5. CHECK en prestamos.total_financiamiento > 0
ALTER TABLE public.prestamos
    DROP CONSTRAINT IF EXISTS ck_prestamos_monto_positivo;
ALTER TABLE public.prestamos
    ADD CONSTRAINT ck_prestamos_monto_positivo
    CHECK (total_financiamiento > 0);

-- 6. CHECK en prestamos.numero_cuotas (entre 1 y 12)
ALTER TABLE public.prestamos
    DROP CONSTRAINT IF EXISTS ck_prestamos_numero_cuotas_rango;
ALTER TABLE public.prestamos
    ADD CONSTRAINT ck_prestamos_numero_cuotas_rango
    CHECK (numero_cuotas >= 1 AND numero_cuotas <= 12);

-- 7. CHECK en prestamos.estado (valores permitidos)
ALTER TABLE public.prestamos
    DROP CONSTRAINT IF EXISTS ck_prestamos_estado_valido;
ALTER TABLE public.prestamos
    ADD CONSTRAINT ck_prestamos_estado_valido
    CHECK (estado IN ('DRAFT', 'EN_REVISION', 'APROBADO', 'DESEMBOLSADO', 'EVALUADO'));
