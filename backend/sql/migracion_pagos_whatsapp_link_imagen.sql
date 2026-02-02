-- Migración: link de imagen (Google Drive) en pagos_whatsapp + estado conversación cobranza + pagos_informes
-- Ejecutar en la BD si la tabla pagos_whatsapp ya existe.

-- 1) Columna link_imagen en pagos_whatsapp (ruta/URL de imagen guardada, ej. Google Drive)
ALTER TABLE pagos_whatsapp ADD COLUMN IF NOT EXISTS link_imagen TEXT;

-- 2) Estado de conversación por teléfono (flujo cobranza: cédula EVJ → foto papeleta hasta 3 intentos)
CREATE TABLE IF NOT EXISTS conversacion_cobranza (
    id SERIAL PRIMARY KEY,
    telefono VARCHAR(30) NOT NULL UNIQUE,
    cedula VARCHAR(20),
    estado VARCHAR(30) NOT NULL DEFAULT 'esperando_cedula',
    intento_foto INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_conversacion_cobranza_telefono ON conversacion_cobranza (telefono);
CREATE INDEX IF NOT EXISTS ix_conversacion_cobranza_estado ON conversacion_cobranza (estado);

-- 3) Tabla pagos_informes: digitalización OCR (cedula, fecha, banco, numero_deposito, cantidad, link_imagen)
CREATE TABLE IF NOT EXISTS pagos_informes (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    fecha_deposito VARCHAR(50),
    nombre_banco VARCHAR(255),
    numero_deposito VARCHAR(100),
    cantidad VARCHAR(50),
    link_imagen TEXT NOT NULL,
    pagos_whatsapp_id INTEGER REFERENCES pagos_whatsapp(id) ON DELETE SET NULL,
    periodo_envio VARCHAR(20) NOT NULL,
    fecha_informe TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_pagos_informes_cedula ON pagos_informes (cedula);
CREATE INDEX IF NOT EXISTS ix_pagos_informes_periodo_envio ON pagos_informes (periodo_envio);
CREATE INDEX IF NOT EXISTS ix_pagos_informes_fecha_informe ON pagos_informes (fecha_informe);
