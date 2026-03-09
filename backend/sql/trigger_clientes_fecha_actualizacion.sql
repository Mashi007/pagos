-- Trigger: actualizar fecha_actualizacion en cada UPDATE de clientes
-- Así cualquier actualización (API o SQL directo) deja registrada la última modificación.
-- Ejecutar en la BD: psql $DATABASE_URL -f backend/sql/trigger_clientes_fecha_actualizacion.sql

DROP TRIGGER IF EXISTS trg_clientes_fecha_actualizacion ON public.clientes;
DROP FUNCTION IF EXISTS public.fn_clientes_actualizar_fecha_actualizacion();

CREATE OR REPLACE FUNCTION public.fn_clientes_actualizar_fecha_actualizacion()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.fecha_actualizacion = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_clientes_fecha_actualizacion
  BEFORE UPDATE ON public.clientes
  FOR EACH ROW
  EXECUTE PROCEDURE public.fn_clientes_actualizar_fecha_actualizacion();

-- Comentario: el backend también asigna fecha_actualizacion en cada PUT;
-- este trigger asegura consistencia si se actualiza por otro medio (SQL, migraciones, etc.).
