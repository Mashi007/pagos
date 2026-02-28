-- Tabla temporal para datos de conciliación cargados desde Excel.
-- Se llena al "Guardar e integrar" desde la interfaz de Reporte Conciliación.
-- Se vacía automáticamente al descargar el Excel del reporte.

CREATE TABLE IF NOT EXISTS conciliacion_temporal (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    total_financiamiento NUMERIC(14, 2) NOT NULL,
    total_abonos NUMERIC(14, 2) NOT NULL,
    columna_e VARCHAR(255) NULL,
    columna_f VARCHAR(255) NULL,
    creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_conciliacion_temporal_cedula ON conciliacion_temporal (cedula);

COMMENT ON TABLE conciliacion_temporal IS 'Datos de Excel de conciliación por cédula; se eliminan al descargar el reporte.';
