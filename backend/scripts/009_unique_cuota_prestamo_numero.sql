-- Migración 009: UniqueConstraint en cuotas(prestamo_id, numero_cuota)
-- Previene la creación de cuotas duplicadas para el mismo préstamo y número de cuota.
-- Ejecutar en producción antes de desplegar el código que usa _generar_cuotas_amortizacion.

-- 1. Verificar duplicados existentes (debe retornar 0 filas antes de aplicar la constraint)
-- SELECT prestamo_id, numero_cuota, COUNT(*) AS total
-- FROM public.cuotas
-- GROUP BY prestamo_id, numero_cuota
-- HAVING COUNT(*) > 1;

-- 2. Eliminar la constraint si ya existe de una migración anterior
ALTER TABLE public.cuotas
    DROP CONSTRAINT IF EXISTS uq_cuotas_prestamo_numero_cuota;

-- 3. Crear la constraint única
ALTER TABLE public.cuotas
    ADD CONSTRAINT uq_cuotas_prestamo_numero_cuota
    UNIQUE (prestamo_id, numero_cuota);
