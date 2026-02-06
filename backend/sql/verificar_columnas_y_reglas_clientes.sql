-- =============================================================================
-- VERIFICAR COLUMNAS Y REGLAS DE NEGOCIO - Tabla clientes (ejecutar en DBeaver)
-- INSTRUCCIÓN: Ejecutar SOLO hasta la línea "FIN". Cuando veas el listado de
--             columnas (A), escribe "fin" y después ejecuta el resto (B en adelante).
-- Referencia: docs/REGLAS_NEGOCIO_CLIENTES.md y app.models.cliente.Cliente
-- =============================================================================

-- -----------------------------------------------------------------------------
-- A) COLUMNAS: existencia y tipo según modelo
-- -----------------------------------------------------------------------------
SELECT column_name,
       data_type,
       character_maximum_length AS max_length,
       is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'clientes'
ORDER BY ordinal_position;

-- Columnas esperadas: id, cedula(20), nombres(100), telefono(100), email(100),
-- direccion(text), fecha_nacimiento(date), ocupacion(100), estado(20),
-- fecha_registro(timestamp), fecha_actualizacion(timestamp), usuario_registro(50), notas(text)

-- FIN
-- ========== No proceses el resto hasta ver el resultado anterior y escribir fin ==========


-- -----------------------------------------------------------------------------
-- B) REGLA: Estado solo ACTIVO | INACTIVO | MORA | FINALIZADO
-- -----------------------------------------------------------------------------
-- Valores distintos de estado y cantidad (no debe haber otros)
SELECT estado, COUNT(*) AS cantidad
FROM public.clientes
GROUP BY estado
ORDER BY estado;

-- Si aparece algún valor distinto de los 4 anteriores, incumple la regla.


-- -----------------------------------------------------------------------------
-- C) REGLA: No duplicados por (cedula + nombres)
-- -----------------------------------------------------------------------------
-- Duplicados: mismo par cedula + nombres (debería estar vacío si se cumple la regla)
SELECT cedula, nombres, COUNT(*) AS repeticiones, array_agg(id ORDER BY id) AS ids
FROM public.clientes
GROUP BY cedula, nombres
HAVING COUNT(*) > 1
ORDER BY repeticiones DESC;


-- -----------------------------------------------------------------------------
-- D) REGLA: No duplicados por email (cuando email no está vacío)
-- -----------------------------------------------------------------------------
-- Duplicados: mismo email no vacío (debería estar vacío si se cumple la regla)
SELECT email, COUNT(*) AS repeticiones, array_agg(id ORDER BY id) AS ids
FROM public.clientes
WHERE TRIM(COALESCE(email, '')) <> ''
GROUP BY email
HAVING COUNT(*) > 1
ORDER BY repeticiones DESC;


-- -----------------------------------------------------------------------------
-- E) REGLA: Campos obligatorios sin NULL (esquema NOT NULL)
-- -----------------------------------------------------------------------------
-- Conteo de filas con NULL en campos que deben ser NOT NULL (esperado: 0 en cada uno)
SELECT
  (SELECT COUNT(*) FROM public.clientes WHERE id IS NULL) AS nulls_id,
  (SELECT COUNT(*) FROM public.clientes WHERE cedula IS NULL OR TRIM(cedula) = '') AS nulls_cedula,
  (SELECT COUNT(*) FROM public.clientes WHERE nombres IS NULL OR TRIM(nombres) = '') AS nulls_nombres,
  (SELECT COUNT(*) FROM public.clientes WHERE telefono IS NULL OR TRIM(telefono) = '') AS nulls_telefono,
  (SELECT COUNT(*) FROM public.clientes WHERE email IS NULL) AS nulls_email,
  (SELECT COUNT(*) FROM public.clientes WHERE direccion IS NULL) AS nulls_direccion,
  (SELECT COUNT(*) FROM public.clientes WHERE fecha_nacimiento IS NULL) AS nulls_fecha_nacimiento,
  (SELECT COUNT(*) FROM public.clientes WHERE ocupacion IS NULL OR TRIM(ocupacion) = '') AS nulls_ocupacion,
  (SELECT COUNT(*) FROM public.clientes WHERE estado IS NULL OR TRIM(estado) = '') AS nulls_estado,
  (SELECT COUNT(*) FROM public.clientes WHERE fecha_registro IS NULL) AS nulls_fecha_registro,
  (SELECT COUNT(*) FROM public.clientes WHERE fecha_actualizacion IS NULL) AS nulls_fecha_actualizacion,
  (SELECT COUNT(*) FROM public.clientes WHERE usuario_registro IS NULL OR TRIM(usuario_registro) = '') AS nulls_usuario_registro,
  (SELECT COUNT(*) FROM public.clientes WHERE notas IS NULL) AS nulls_notas;


-- -----------------------------------------------------------------------------
-- F) REGLA: Longitudes máximas (cedula 20, nombres 100, telefono 100, email 100, ocupacion 100, estado 20, usuario_registro 50)
-- -----------------------------------------------------------------------------
-- Filas que exceden longitud (esperado: 0 filas)
SELECT id, cedula, nombres, telefono, email, ocupacion, estado, usuario_registro,
       LENGTH(cedula) AS len_cedula,
       LENGTH(nombres) AS len_nombres,
       LENGTH(telefono) AS len_telefono,
       LENGTH(email) AS len_email,
       LENGTH(ocupacion) AS len_ocupacion,
       LENGTH(estado) AS len_estado,
       LENGTH(usuario_registro) AS len_usuario_registro
FROM public.clientes
WHERE LENGTH(TRIM(cedula)) > 20
   OR LENGTH(TRIM(nombres)) > 100
   OR LENGTH(TRIM(telefono)) > 100
   OR LENGTH(TRIM(email)) > 100
   OR LENGTH(TRIM(ocupacion)) > 100
   OR LENGTH(TRIM(estado)) > 20
   OR LENGTH(TRIM(usuario_registro)) > 50;


-- -----------------------------------------------------------------------------
-- G) RESUMEN DE CUMPLIMIENTO (interpretar resultados)
-- -----------------------------------------------------------------------------
-- B: Solo deben aparecer ACTIVO, INACTIVO, MORA, FINALIZADO.
-- C: Resultado vacío = sin duplicados cedula+nombres.
-- D: Resultado vacío = sin duplicados email.
-- E: Todos los contadores en 0 = sin NULL en obligatorios.
-- F: Resultado vacío = nadie excede longitudes máximas.
