-- Correccion puntual V27232010: recibos leen prestamos.nombres (snapshot).
-- Estado de cuenta lee clientes.nombres (ya correcto: Yosmary...).
-- Ejecutar una sola vez en produccion si prestamos.nombres sigue con typo Yosmery.

UPDATE prestamos
SET nombres = 'Yosmary Del Carmen Cardenas Hernandez'
WHERE cedula = 'V27232010'
  AND nombres IS DISTINCT FROM 'Yosmary Del Carmen Cardenas Hernandez';

UPDATE clientes
SET nombres = 'Yosmary Del Carmen Cardenas Hernandez'
WHERE cedula = 'V27232010'
  AND nombres IS DISTINCT FROM 'Yosmary Del Carmen Cardenas Hernandez';
