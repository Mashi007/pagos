-- Tabla datos_importados_conerrores
-- Registros que no cumplen validadores al "Importar reportados aprobados (Cobros)".
-- Se acumulan hasta que el usuario descarga Excel; al descargar se vacía la tabla.
-- Ejecutar en DBeaver (PostgreSQL).

CREATE TABLE IF NOT EXISTS datos_importados_conerrores (
    id                  SERIAL PRIMARY KEY,
    cedula_cliente       VARCHAR(20) NULL,
    prestamo_id          INTEGER NULL,
    fecha_pago           TIMESTAMP NOT NULL,
    monto_pagado         NUMERIC(14, 2) NOT NULL,
    numero_documento     VARCHAR(100) NULL,
    estado               VARCHAR(30) NULL DEFAULT 'PENDIENTE',
    referencia_pago      VARCHAR(100) NOT NULL DEFAULT '',
    errores_descripcion  JSONB NULL,
    observaciones        VARCHAR(255) NULL,
    fila_origen          INTEGER NULL,
    referencia_interna   VARCHAR(100) NULL,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE datos_importados_conerrores IS
  'Fallos de Importar reportados aprobados (Cobros). Se vacía al descargar Excel.';

CREATE INDEX IF NOT EXISTS ix_datos_importados_conerrores_cedula_cliente
    ON datos_importados_conerrores (cedula_cliente);

CREATE INDEX IF NOT EXISTS ix_datos_importados_conerrores_prestamo_id
    ON datos_importados_conerrores (prestamo_id);
