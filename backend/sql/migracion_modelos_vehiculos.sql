-- Tabla modelos_vehiculos: catálogo de modelos con precio para cargar Valor Activo en Nuevo Préstamo.
-- Ejecutar en la BD antes de usar CRUD de modelos en /modelos-vehiculos.

CREATE TABLE IF NOT EXISTS modelos_vehiculos (
    id SERIAL PRIMARY KEY,
    modelo VARCHAR(255) NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT true,
    precio NUMERIC(14, 2) NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_modelos_vehiculos_id ON modelos_vehiculos (id);
CREATE INDEX IF NOT EXISTS ix_modelos_vehiculos_modelo ON modelos_vehiculos (modelo);
CREATE INDEX IF NOT EXISTS ix_modelos_vehiculos_activo ON modelos_vehiculos (activo);

COMMENT ON TABLE modelos_vehiculos IS 'Catálogo de modelos de vehículos con precio; al seleccionar en Nuevo Préstamo se carga el precio en Valor Activo.';

-- Opcional: rellenar con nombres que ya existan en préstamos (precio NULL; luego se puede editar en /modelos-vehiculos)
-- (precio debe ser NULL::numeric para que PostgreSQL no infiera tipo text)
-- INSERT INTO modelos_vehiculos (modelo, activo, precio)
-- SELECT DISTINCT TRIM(modelo_vehiculo), true, NULL::numeric(14,2)
-- FROM prestamos
-- WHERE modelo_vehiculo IS NOT NULL AND TRIM(modelo_vehiculo) <> ''
-- ON CONFLICT (modelo) DO NOTHING;
