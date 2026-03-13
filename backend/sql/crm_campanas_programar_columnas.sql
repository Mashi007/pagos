-- Campañas CRM: columnas para envío programado (cada X días/horas).
-- Ejecutar si la tabla crm_campana ya existe y no tiene estas columnas.

-- SQLite (ejecutar una por una):
-- ALTER TABLE crm_campana ADD COLUMN programado_cada_dias INTEGER;
-- ALTER TABLE crm_campana ADD COLUMN programado_cada_horas INTEGER;
-- ALTER TABLE crm_campana ADD COLUMN programado_proxima_ejecucion DATETIME;

-- PostgreSQL (ejecutar cada ALTER por separado si IF NOT EXISTS no está disponible):
ALTER TABLE crm_campana ADD COLUMN IF NOT EXISTS programado_cada_dias INTEGER;
ALTER TABLE crm_campana ADD COLUMN IF NOT EXISTS programado_cada_horas INTEGER;
ALTER TABLE crm_campana ADD COLUMN IF NOT EXISTS programado_proxima_ejecucion TIMESTAMP;
