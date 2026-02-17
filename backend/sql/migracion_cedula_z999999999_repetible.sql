-- =============================================================================
-- Migración: Permitir múltiples clientes con cédula Z999999999 (sin cédula)
-- Reemplaza UNIQUE(cedula) por índice único parcial que excluye Z999999999.
-- Ejecutar en DBeaver sobre la BD del proyecto.
-- =============================================================================

-- 1) Eliminar el constraint UNIQUE existente (si existe)
ALTER TABLE public.clientes
  DROP CONSTRAINT IF EXISTS uq_clientes_cedula;

-- 2) Crear índice único parcial: solo aplica cuando cedula <> 'Z999999999'
--    Así, Z999999999 puede repetirse; el resto de cédulas siguen siendo únicas.
CREATE UNIQUE INDEX uq_clientes_cedula_sin_z
  ON public.clientes (cedula)
  WHERE cedula <> 'Z999999999';

-- Verificar: SELECT * FROM pg_indexes WHERE tablename = 'clientes';
