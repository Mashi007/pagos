-- Migración 012: tabla envios_notificacion (estadísticas y rebotados por pestaña)
-- Ejecutar en DBeaver si no usas: alembic upgrade head

-- UPGRADE: crear tabla e índices
CREATE TABLE envios_notificacion (
    id SERIAL NOT NULL,
    fecha_envio TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    tipo_tab VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    nombre VARCHAR(255),
    cedula VARCHAR(50),
    exito BOOLEAN NOT NULL,
    error_mensaje TEXT,
    PRIMARY KEY (id)
);

CREATE INDEX ix_envios_notificacion_id ON envios_notificacion (id);
CREATE INDEX ix_envios_notificacion_tipo_tab ON envios_notificacion (tipo_tab);

-- Para revertir (DOWNGRADE), ejecutar en orden inverso:
-- DROP INDEX IF EXISTS ix_envios_notificacion_tipo_tab;
-- DROP INDEX IF EXISTS ix_envios_notificacion_id;
-- DROP TABLE IF EXISTS envios_notificacion;
