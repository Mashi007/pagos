-- Verificar si todos los préstamos tienen cuotas generadas
-- Tablas: prestamos, cuotas (cuotas.prestamo_id → prestamos.id)

-- Resumen: total préstamos, cuántos tienen al menos una cuota, cuántos no tienen
SELECT
    (SELECT COUNT(*) FROM prestamos) AS total_prestamos,
    (SELECT COUNT(DISTINCT prestamo_id) FROM cuotas) AS prestamos_con_cuotas,
    (SELECT COUNT(*) FROM prestamos p
     WHERE NOT EXISTS (SELECT 1 FROM cuotas c WHERE c.prestamo_id = p.id)
    ) AS prestamos_sin_cuotas,
    (NOT EXISTS (
        SELECT 1 FROM prestamos p
        WHERE NOT EXISTS (SELECT 1 FROM cuotas c WHERE c.prestamo_id = p.id)
    )) AS todos_tienen_cuotas;

-- Listado de préstamos SIN cuotas generadas (solo id)
SELECT p.id
FROM prestamos p
WHERE NOT EXISTS (SELECT 1 FROM cuotas c WHERE c.prestamo_id = p.id)
ORDER BY p.id DESC;
