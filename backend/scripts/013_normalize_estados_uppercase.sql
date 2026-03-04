-- Migración 013: Normalizar TODOS los estados de cuota a MAYÚSCULAS
-- El backend usa MAYÚSCULAS; revision_manual.py ya fue actualizado.
-- Esta migración limpia datos legacy en BD.

-- 1. Normalizar estados en cuotas a MAYÚSCULAS
UPDATE public.cuotas
SET estado = UPPER(estado)
WHERE estado IS NOT NULL;

-- 2. Normalizar estados en pagos a MAYÚSCULAS
UPDATE public.pagos
SET estado = UPPER(estado)
WHERE estado IS NOT NULL;

-- 3. Normalizar estados en prestamos a MAYÚSCULAS
UPDATE public.prestamos
SET estado = UPPER(estado)
WHERE estado IS NOT NULL;

-- 4. Agregar CHECK para forzar MAYÚSCULAS en cuotas (ya hecho en 010_check_constraints.sql)
-- Verificar que todos los estados cumplan:
-- SELECT DISTINCT estado FROM cuotas;  -- Debe mostrar solo MAYÚSCULAS
