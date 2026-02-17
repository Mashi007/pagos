-- =============================================================================
-- Triggers en clientes_temp: mismas reglas que tabla clientes
-- nombres vacío → "Revisar Nombres"
-- telefono vacío/inválido/duplicado → "+589999999999"
-- email vacío/duplicado → "revisar@email.com"
-- Ejecutar en DBeaver.
-- =============================================================================

-- Eliminar triggers anteriores si existen
DROP TRIGGER IF EXISTS trg_clientes_temp_reglas ON public.clientes_temp;
DROP FUNCTION IF EXISTS public.fn_clientes_temp_aplicar_reglas();

-- Función que aplica las reglas antes de INSERT/UPDATE
CREATE OR REPLACE FUNCTION public.fn_clientes_temp_aplicar_reglas()
RETURNS TRIGGER AS $$
DECLARE
  dig TEXT;
  eff_dig TEXT;
  existe_email INT;
  existe_tel INT;
BEGIN
  -- 1) nombres vacío → "Revisar Nombres"
  IF NEW.nombres IS NULL OR TRIM(COALESCE(NEW.nombres, '')) = '' THEN
    NEW.nombres := 'Revisar Nombres';
  END IF;

  -- 2) telefono: vacío o formato inválido → "+589999999999"
  dig := regexp_replace(COALESCE(NEW.telefono, ''), '[^0-9]', '', 'g');
  IF dig LIKE '58%' AND LENGTH(dig) > 10 THEN
    eff_dig := substring(dig from 3);
  ELSE
    eff_dig := dig;
  END IF;

  IF NEW.telefono IS NULL OR TRIM(COALESCE(NEW.telefono, '')) = ''
     OR LENGTH(eff_dig) != 10 OR eff_dig !~ '^[1-9][0-9]{9}$' THEN
    NEW.telefono := '+589999999999';
  ELSE
    -- 2b) telefono duplicado → "+589999999999"
    SELECT 1 INTO existe_tel FROM public.clientes_temp t
    WHERE t.telefono IS NOT NULL AND TRIM(t.telefono) != ''
      AND t.telefono != '+589999999999'
      AND (CASE WHEN regexp_replace(t.telefono, '[^0-9]', '', 'g') LIKE '58%'
                     AND LENGTH(regexp_replace(t.telefono, '[^0-9]', '', 'g')) > 10
                THEN substring(regexp_replace(t.telefono, '[^0-9]', '', 'g') from 3)
                ELSE regexp_replace(t.telefono, '[^0-9]', '', 'g')
           END) = eff_dig
      AND (TG_OP != 'UPDATE' OR t.ctid != OLD.ctid)
    LIMIT 1;
    IF existe_tel = 1 THEN
      NEW.telefono := '+589999999999';
    END IF;
  END IF;

  -- 3) email vacío → "revisar@email.com"
  IF NEW.email IS NULL OR TRIM(COALESCE(NEW.email, '')) = '' THEN
    NEW.email := 'revisar@email.com';
  ELSE
    -- 3b) email duplicado → "revisar@email.com"
    SELECT 1 INTO existe_email FROM public.clientes_temp t
    WHERE LOWER(TRIM(t.email)) = LOWER(TRIM(NEW.email))
      AND LOWER(TRIM(t.email)) != 'revisar@email.com'
      AND (TG_OP != 'UPDATE' OR t.ctid != OLD.ctid)
    LIMIT 1;
    IF existe_email = 1 THEN
      NEW.email := 'revisar@email.com';
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger BEFORE INSERT OR UPDATE
-- Nota: Si usas PostgreSQL < 11, cambia EXECUTE FUNCTION por EXECUTE PROCEDURE
CREATE TRIGGER trg_clientes_temp_reglas
  BEFORE INSERT OR UPDATE ON public.clientes_temp
  FOR EACH ROW
  EXECUTE FUNCTION public.fn_clientes_temp_aplicar_reglas();

-- =============================================================================
-- Requisito: clientes_temp debe tener columnas nombres, telefono, email.
-- Si no existe, crear con misma estructura que clientes:
-- CREATE TABLE public.clientes_temp (LIKE public.clientes INCLUDING DEFAULTS);
-- ALTER TABLE public.clientes_temp DROP COLUMN IF EXISTS id;
