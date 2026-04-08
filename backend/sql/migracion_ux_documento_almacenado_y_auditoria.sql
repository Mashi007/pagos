-- =============================================================================
-- Unicidad del documento almacenado + notas de auditoría (usuario_registro)
-- =============================================================================
--
-- Regla de negocio: no puede repetirse el MISMO valor guardado en
-- `numero_documento` (incluye comprobante normalizado + sufijo interno §CD:
-- + código, o el texto final tras sufijos admin tipo _A#### en carga masiva).
-- Eso NO es "duplicar con permiso": cada fila tiene una clave distinta en BD.
--
-- Auditoría: quien inserta el registro debe quedar en `usuario_registro`
-- (email / identificador desde JWT). En la API ya se rellena al crear `pagos`;
-- conviene lo mismo en `pagos_con_errores` (código).
--
-- IMPORTANTE: ejecute primero los SELECT de diagnóstico. Si hay duplicados,
-- CREATE UNIQUE INDEX fallará hasta resolverlos.
--
-- PostgreSQL. Ajuste schema si no usa public.
-- =============================================================================
--
-- DBeaver / “Updated Rows: 0”
-- Si ejecuta TODO el archivo y casi solo ve comentarios + bloque /* ... */,
-- la BD no aplica cambios: es normal ver 0 filas actualizadas. Los SELECT
-- devuelven filas en la pestaña de resultados (no cuentan como UPDATE).
-- Abajo hay consultas YA ACTIVAS para diagnóstico. Los CREATE INDEX siguen
-- comentados: ejecútelos aparte cuando pagos_docs_duplicados y
-- cola_docs_duplicados sean 0.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0) Resumen: ¿cuántas claves de documento están repetidas? (1 fila de salida)
-- -----------------------------------------------------------------------------
SELECT
  (
    SELECT COUNT(*)::bigint
    FROM (
      SELECT 1
      FROM public.pagos
      WHERE numero_documento IS NOT NULL
        AND btrim(numero_documento) <> ''
      GROUP BY btrim(numero_documento)
      HAVING COUNT(*) > 1
    ) AS d
  ) AS pagos_docs_duplicados,
  (
    SELECT COUNT(*)::bigint
    FROM (
      SELECT 1
      FROM public.pagos_con_errores
      WHERE numero_documento IS NOT NULL
        AND btrim(numero_documento) <> ''
      GROUP BY btrim(numero_documento)
      HAVING COUNT(*) > 1
    ) AS d
  ) AS cola_docs_duplicados;

-- -----------------------------------------------------------------------------
-- 1) Detalle: duplicados en pagos (vacío = bien)
-- -----------------------------------------------------------------------------
SELECT btrim(numero_documento) AS doc, COUNT(*) AS n
FROM public.pagos
WHERE numero_documento IS NOT NULL AND btrim(numero_documento) <> ''
GROUP BY btrim(numero_documento)
HAVING COUNT(*) > 1
ORDER BY n DESC, doc;

-- -----------------------------------------------------------------------------
-- 2) Detalle: duplicados en pagos_con_errores (vacío = bien)
-- -----------------------------------------------------------------------------
SELECT btrim(numero_documento) AS doc, COUNT(*) AS n
FROM public.pagos_con_errores
WHERE numero_documento IS NOT NULL AND btrim(numero_documento) <> ''
GROUP BY btrim(numero_documento)
HAVING COUNT(*) > 1
ORDER BY n DESC, doc;

-- -----------------------------------------------------------------------------
-- 3) Filas sin usuario_registro (máx. 200 por tabla; informativo)
-- -----------------------------------------------------------------------------
SELECT id, numero_documento, fecha_registro
FROM public.pagos
WHERE usuario_registro IS NULL OR btrim(usuario_registro) = ''
ORDER BY id DESC
LIMIT 200;

SELECT id, numero_documento, fecha_registro
FROM public.pagos_con_errores
WHERE usuario_registro IS NULL OR btrim(usuario_registro) = ''
ORDER BY id DESC
LIMIT 200;

-- -----------------------------------------------------------------------------
-- 4) Backfill suave de usuario_registro NULL (ajuste el literal a su política)
-- -----------------------------------------------------------------------------
-- UPDATE public.pagos
-- SET usuario_registro = 'legacy-sin-usuario@sistema'
-- WHERE usuario_registro IS NULL OR btrim(usuario_registro) = '';
--
-- UPDATE public.pagos_con_errores
-- SET usuario_registro = 'legacy-sin-usuario@sistema'
-- WHERE usuario_registro IS NULL OR btrim(usuario_registro) = '';

-- -----------------------------------------------------------------------------
-- 5) y 6) Índices únicos (DESCOMENTE solo si el diagnóstico 1-2 no devuelve filas)
-- -----------------------------------------------------------------------------
-- Índice parcial: ignora NULL y cadenas vacías.
-- La API escribe `numero_documento` ya compuesto; btrim alinea espacios legacy.
--
-- Si prefiere unicidad byte-a-byte con lo que guarda la API (sin expresión):
--   CREATE UNIQUE INDEX ... ON public.pagos (numero_documento)
--   WHERE numero_documento IS NOT NULL AND btrim(numero_documento) <> '';
--
/*
DROP INDEX IF EXISTS public.ux_pagos_numero_documento_btrim;

CREATE UNIQUE INDEX ux_pagos_numero_documento_btrim
  ON public.pagos ((btrim(numero_documento)))
  WHERE numero_documento IS NOT NULL AND btrim(numero_documento) <> '';

DROP INDEX IF EXISTS public.ux_pagos_con_errores_numero_documento_btrim;

CREATE UNIQUE INDEX ux_pagos_con_errores_numero_documento_btrim
  ON public.pagos_con_errores ((btrim(numero_documento)))
  WHERE numero_documento IS NOT NULL AND btrim(numero_documento) <> '';
*/

-- Nota: el mismo texto podría existir en `pagos` y en `pagos_con_errores` si algo
-- bypass la API; `numero_documento_ya_registrado` en código evita solapamiento al crear.
