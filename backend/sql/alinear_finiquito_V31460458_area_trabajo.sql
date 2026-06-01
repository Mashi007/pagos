-- V31460458 / prestamo 1048: volver a area de REVISION si bajo a trabajo sin terminar conciliacion.

SELECT fc.id, fc.estado AS caso_estado,
       p.estado_gestion_finiquito, p.finiquito_tramite_fecha_limite
FROM finiquito_casos fc
JOIN prestamos p ON p.id = fc.prestamo_id
WHERE fc.prestamo_id = 1048;

-- Devolver a area de revision (ACEPTADO) — no es bandeja REVISION:
UPDATE finiquito_casos
SET estado = 'ACEPTADO'
WHERE prestamo_id = 1048 AND id = 1479;

UPDATE prestamos
SET estado_gestion_finiquito = 'ACEPTADO',
    finiquito_tramite_fecha_limite = NULL
WHERE id = 1048;

-- Verificar: caso_estado = ACEPTADO, prestamo ACEPTADO
-- En gestion: pestana "Area de revision", cedula V31460458, Visto/Continuar si aplica.
