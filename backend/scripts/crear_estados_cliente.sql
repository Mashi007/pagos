-- =============================================================================
-- Crear tabla estados_cliente para que la app tome los estados desde la BD
-- Ejecutar en DBeaver contra la base de datos de RapiCredit
-- =============================================================================

-- Crear tabla si no existe
CREATE TABLE IF NOT EXISTS estados_cliente (
    valor VARCHAR(20) PRIMARY KEY,
    etiqueta VARCHAR(50) NOT NULL,
    orden INTEGER NOT NULL DEFAULT 0
);

-- Insertar estados (ignorar si ya existen)
INSERT INTO estados_cliente (valor, etiqueta, orden) VALUES
    ('ACTIVO', 'Activo', 1),
    ('INACTIVO', 'Inactivo', 2),
    ('FINALIZADO', 'Finalizado', 3),
    ('LEGACY', 'Legacy', 4)
ON CONFLICT (valor) DO NOTHING;
