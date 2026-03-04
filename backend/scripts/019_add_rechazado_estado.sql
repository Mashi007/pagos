-- Migration: 019_add_rechazado_estado.sql
-- Propósito: Agregar 'RECHAZADO' como estado válido en préstamos
-- Utilidad: Permitir rechazar préstamos en revisión

BEGIN;

-- 1. Actualizar CHECK constraint para incluir RECHAZADO
ALTER TABLE public.prestamos
DROP CONSTRAINT ck_prestamos_estado_valido;

ALTER TABLE public.prestamos
ADD CONSTRAINT ck_prestamos_estado_valido
CHECK (estado IN ('DRAFT', 'EN_REVISION', 'APROBADO', 'DESEMBOLSADO', 'EVALUADO', 'RECHAZADO'));

-- 2. Actualizar cuotas.estado CHECK para incluir RECHAZADO (opcional, para casos especiales)
ALTER TABLE public.cuotas
DROP CONSTRAINT IF EXISTS ck_cuotas_estado_valido;

ALTER TABLE public.cuotas
ADD CONSTRAINT ck_cuotas_estado_valido
CHECK (estado IN ('PENDIENTE', 'PAGADO', 'PAGO_ADELANTADO', 'VENCIDO', 'MORA', 'RECHAZADO'));

COMMIT;

-- ============================================================
-- VERIFICACIÓN
-- ============================================================

-- Ver que constraint fue actualizado:
SELECT constraint_name, table_name
FROM information_schema.table_constraints
WHERE table_name = 'prestamos' AND constraint_name = 'ck_prestamos_estado_valido';

-- Ver estados permitidos en prestamos:
SELECT pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'ck_prestamos_estado_valido';

-- NOTA: Después de esta migración:
-- 1. El backend debe tener el endpoint POST /prestamos/{id}/rechazar implementado
-- 2. Frontend debe mostrar opción de RECHAZADO en estados
-- 3. Migración de datos: Cualquier prestamo existente con estado='RECHAZADO' ya es válido
