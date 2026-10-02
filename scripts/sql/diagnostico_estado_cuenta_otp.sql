-- Diagnóstico: clientes que no reciben OTP de estado de cuenta (PostgreSQL)
-- Ejecutar en DBeaver / psql contra la BD de producción.

-- 1) Configuración email (tabla configuracion, claves habituales)
SELECT clave, valor
FROM configuracion
WHERE clave IN (
  'email_config',
  'email_config_cuentas',
  'estado_cuenta_codigo_email'
)
ORDER BY clave;

-- En email_config / email_config_cuentas (JSON) revisar manualmente:
--   email_activo = true
--   email_activo_estado_cuenta = true
--   modo_pruebas_estado_cuenta = false  (si true, OTP no va al cliente salvo prueba manual)
--   Cuenta SMTP asignada a servicio estado_cuenta (índice 2 en asignación típica)

-- 2) Clientes con préstamo elegible pero sin correo enrutable (ASCII / sin mojibake U+FFFD)
--    emails_destino_desde_objeto descarta non-ASCII y U+FFFD
SELECT c.id,
       c.cedula,
       c.email,
       c.email_secundario,
       COUNT(p.id) AS prestamos_aprobado_o_liquidado
FROM clientes c
JOIN prestamos p ON p.cliente_id = c.id
WHERE upper(trim(coalesce(p.estado, ''))) IN ('APROBADO', 'LIQUIDADO')
  AND (
        coalesce(trim(c.email), '') = ''
     OR c.email !~ '^[[:ascii:]]+@[[:ascii:]]+$'
     OR position(U&'\FFFD' IN coalesce(c.email, '')) > 0
     OR (
          coalesce(trim(c.email_secundario), '') <> ''
          AND (
                c.email_secundario !~ '^[[:ascii:]]+@[[:ascii:]]+$'
             OR position(U&'\FFFD' IN c.email_secundario) > 0
          )
          AND (
                coalesce(trim(c.email), '') = ''
             OR c.email !~ '^[[:ascii:]]+@[[:ascii:]]+$'
             OR position(U&'\FFFD' IN coalesce(c.email, '')) > 0
          )
        )
      )
GROUP BY c.id, c.cedula, c.email, c.email_secundario
ORDER BY c.cedula
LIMIT 200;

-- 3) Códigos OTP recientes (se crean aunque falle SMTP; si hay filas y el cliente no recibe mail → SMTP/config)
SELECT id,
       cedula_normalizada,
       left(email, 3) || '***' AS email_mask,
       usado,
       creado_en,
       expira_en
FROM estado_cuenta_codigos
WHERE creado_en >= (now() AT TIME ZONE 'utc') - interval '7 days'
ORDER BY creado_en DESC
LIMIT 100;

-- 4) Logs backend (Render): buscar en logs de la API
--   estado_cuenta solicitar: codigo NO enviado
--   outcome=fail reason=servicio_email_desactivado
--   outcome=fail reason=smtp
--   outcome=fail reason=sin_email_valido
