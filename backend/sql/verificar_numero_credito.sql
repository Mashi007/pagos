-- =============================================================================
-- Número de crédito: origen y comprobación
-- =============================================================================
-- El "número de crédito" en la app es el ID del préstamo: prestamos.id (PK).
-- NO es el número de documento del pago (numero_documento en tabla pagos).
-- El frontend obtiene los créditos por cédula con: GET /api/v1/prestamos/cedula/{cedula}
-- y debe enviar en POST /api/v1/pagos el campo prestamo_id = uno de esos prestamos.id.
--
-- Si envías 96179604 y el backend responde "El crédito #96179604 no existe", es porque
-- 96179604 no es un prestamos.id (suele ser número de documento o cédula por error).
-- =============================================================================

-- 1) Listar créditos (prestamos.id) por cédula: esto es lo que debe usarse como "crédito"
--    Sustituir 'TU_CEDULA' por la cédula del cliente.
SELECT
    p.id          AS numero_credito,  -- Este es el valor correcto para prestamo_id
    p.cedula,
    c.nombres,
    p.estado,
    p.total_financiamiento,
    p.producto
FROM prestamos p
JOIN clientes c ON c.id = p.cliente_id
WHERE UPPER(REPLACE(REPLACE(COALESCE(c.cedula, p.cedula), '-', ''), ' ', ''))
      = UPPER(REPLACE(REPLACE('TU_CEDULA', '-', ''), ' ', ''))
   OR c.cedula = 'TU_CEDULA'
   OR p.cedula = 'TU_CEDULA'
ORDER BY p.id;

-- 2) Comprobar si 96179604 existe como préstamo (id). Si no hay filas, ese no es un crédito válido.
SELECT id, cedula, estado, total_financiamiento, producto
FROM prestamos
WHERE id = 96179604;
-- Resultado esperado: vacío (por eso el backend devuelve 400).

-- 3) Ver si 96179604 aparece como número de documento en pagos (confusión típica)
--    En la BD la columna es "cedula", no cedula_cliente.
SELECT id, cedula, prestamo_id, numero_documento, monto_pagado, fecha_pago
FROM pagos
WHERE numero_documento = '96179604'
   OR numero_documento LIKE '%96179604%'
LIMIT 10;

-- 4) Ver si 96179604 es una cédula en clientes
SELECT id, cedula, nombres FROM clientes WHERE cedula = '96179604' OR cedula LIKE '%96179604%' LIMIT 5;

-- 0) Comprobar si hay datos: conteo por tabla (si prestamos = 0, no hay créditos y POST /pagos con prestamo_id fallará)
SELECT 'prestamos' AS tabla, COUNT(*) AS filas FROM prestamos
UNION ALL
SELECT 'clientes', COUNT(*) FROM clientes
UNION ALL
SELECT 'pagos', COUNT(*) FROM pagos;

-- 5) Listar préstamos que SÍ existen (para ver numero_credito = id y cédulas con crédito)
--    Usa uno de estos id como prestamo_id al registrar un pago. Si esta consulta no devuelve filas, la tabla prestamos está vacía.
SELECT
    p.id AS numero_credito,
    p.cedula,
    c.nombres,
    p.estado,
    p.total_financiamiento,
    p.producto
FROM prestamos p
LEFT JOIN clientes c ON c.id = p.cliente_id
ORDER BY p.id DESC
LIMIT 50;

-- 6) Ejemplo por cédula concreta (sustituir 16835052 por una cédula que exista en prestamos o clientes)
-- SELECT p.id AS numero_credito, p.cedula, c.nombres, p.estado
-- FROM prestamos p
-- JOIN clientes c ON c.id = p.cliente_id
-- WHERE p.cedula = '16835052' OR c.cedula = '16835052';
