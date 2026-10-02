-- Actualiza cuenta 2 en email_config (version 2) a smtp_user cobranza@rapicreditca.com.
-- Ejecutar en produccion si la cuenta 2 sigue como tucuenta@.
-- NO borra smtp_password encriptada; solo cambia identidad del buzon en el JSON.

UPDATE configuracion
SET valor = (
  SELECT jsonb_set(
    jsonb_set(
      jsonb_set(
        valor::jsonb,
        '{cuentas,1,smtp_user}',
        '"cobranza@rapicreditca.com"'
      ),
      '{cuentas,1,from_email}',
      '"cobranza@rapicreditca.com"'
    ),
    '{cuentas,1,imap_user}',
    '"cobranza@rapicreditca.com"'
  )::text
)
WHERE clave = 'email_config'
  AND valor::jsonb->>'version' = '2'
  AND (
    lower(coalesce(valor::jsonb->'cuentas'->1->>'smtp_user', '')) = 'tucuenta@rapicreditca.com'
    OR lower(coalesce(valor::jsonb->'cuentas'->1->>'smtp_user', '')) = ''
  );

-- Verificacion:
-- SELECT valor::jsonb->'cuentas'->1->>'smtp_user' FROM configuracion WHERE clave = 'email_config';
