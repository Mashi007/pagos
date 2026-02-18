-- =============================================================================
-- SQL TOTAL - TODAS LAS INSTRUCCIONES PARA RENDER (PostgreSQL)
-- Ejecutar en orden. Idempotente (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
-- Sirve para BD nueva o existente.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0) usuarios: reemplazo is_admin por rol (administrador | operativo)
-- -----------------------------------------------------------------------------
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS rol VARCHAR(20) NOT NULL DEFAULT 'operativo';
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'usuarios' AND column_name = 'is_admin') THEN
    UPDATE usuarios SET rol = 'administrador' WHERE is_admin = true;
    ALTER TABLE usuarios DROP COLUMN is_admin;
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 1) pagos_whatsapp: columna link_imagen (URL de imagen en Google Drive)
-- -----------------------------------------------------------------------------
ALTER TABLE pagos_whatsapp ADD COLUMN IF NOT EXISTS link_imagen TEXT;

-- -----------------------------------------------------------------------------
-- 2) pagos_informes: tabla (si no existe) y columnas del modelo OCR/informe
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pagos_informes (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    fecha_deposito VARCHAR(50),
    nombre_banco VARCHAR(255),
    numero_deposito VARCHAR(100),
    numero_documento VARCHAR(100),
    cantidad VARCHAR(50),
    humano VARCHAR(20),
    link_imagen TEXT,
    observacion TEXT,
    pagos_whatsapp_id INTEGER REFERENCES pagos_whatsapp(id) ON DELETE SET NULL,
    periodo_envio VARCHAR(20) NOT NULL,
    fecha_informe TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_pagos_informes_cedula ON pagos_informes (cedula);
CREATE INDEX IF NOT EXISTS ix_pagos_informes_periodo_envio ON pagos_informes (periodo_envio);
CREATE INDEX IF NOT EXISTS ix_pagos_informes_fecha_informe ON pagos_informes (fecha_informe);

ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS nombre_banco VARCHAR(255);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS numero_deposito VARCHAR(100);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS numero_documento VARCHAR(100);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS humano VARCHAR(20);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS observacion TEXT;
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS link_imagen TEXT;
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS cantidad VARCHAR(50);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS nombre_cliente VARCHAR(255);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS estado_conciliacion VARCHAR(50);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS telefono VARCHAR(30);
CREATE INDEX IF NOT EXISTS ix_pagos_informes_estado_conciliacion ON pagos_informes (estado_conciliacion);
CREATE INDEX IF NOT EXISTS ix_pagos_informes_telefono ON pagos_informes (telefono);

-- Permitir NULL en banco_entidad_financiera (la app usa nombre_banco; evita NotNullViolation)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'pagos_informes' AND column_name = 'banco_entidad_financiera') THEN
    ALTER TABLE pagos_informes ALTER COLUMN banco_entidad_financiera DROP NOT NULL;
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 3) conversacion_cobranza: tabla (si no existe) y columnas flujo cobranza/confirmación
-- -----------------------------------------------------------------------------
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

ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS nombre_cliente VARCHAR(100);
ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS intento_confirmacion INTEGER NOT NULL DEFAULT 0;
ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS observacion TEXT;
ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS pagos_informe_id_pendiente INTEGER REFERENCES pagos_informes(id) ON DELETE SET NULL;

-- -----------------------------------------------------------------------------
-- 4) tickets: columnas fecha_creacion y fecha_actualizacion (requeridas por el modelo)
-- -----------------------------------------------------------------------------
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
