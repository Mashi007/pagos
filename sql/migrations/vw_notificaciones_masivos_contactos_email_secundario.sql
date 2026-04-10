-- Vista para notificaciones masivas (CRM / pestaña Masivos).
-- Expone correo 1 (email) y correo 2 (email_secundario) para que el backend no dependa solo del fallback a tabla clientes.
--
-- Requisitos: columna clientes.email_secundario (ver migracion add_clientes_email_secundario u homologa).
-- Ejecutar en PostgreSQL. Si la vista no existia, se crea; si existia, se reemplaza.
--
-- Columnas alineadas con backend/app/api/v1/endpoints/notificaciones_tabs.py (get_items_masivos):
--   id, cliente_id, cedula, nombre, email, email_secundario, telefono, updated_at

CREATE OR REPLACE VIEW vw_notificaciones_masivos_contactos AS
SELECT
  c.id AS id,
  c.id AS cliente_id,
  c.cedula,
  c.nombres AS nombre,
  c.email,
  c.email_secundario,
  c.telefono,
  COALESCE(c.fecha_actualizacion, c.fecha_registro) AS updated_at
FROM clientes c
WHERE c.email IS NOT NULL
  AND TRIM(c.email) <> '';

COMMENT ON VIEW vw_notificaciones_masivos_contactos IS
  'Contactos para envios masivos: correo 1 = email, correo 2 = email_secundario; solo filas con email principal no vacio.';
