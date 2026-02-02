-- =============================================================================
-- Tabla definiciones_campos (Catálogo de Campos - Configuración > AI)
-- Ejecutar en DBeaver (o en la BD) si la tabla no se crea con create_all al arrancar.
--
-- NOTA: Si ves mensajes "already exists, skipping" o "does not exist, skipping",
-- son AVISOS normales de PostgreSQL (no errores). La tabla/índices ya existen
-- y el script no hace nada; todo está correcto.
-- =============================================================================

CREATE TABLE IF NOT EXISTS definiciones_campos (
    id SERIAL PRIMARY KEY,
    tabla VARCHAR(200) NOT NULL,
    campo VARCHAR(200) NOT NULL,
    definicion TEXT NOT NULL,
    tipo_dato VARCHAR(100),
    es_obligatorio BOOLEAN NOT NULL DEFAULT FALSE,
    tiene_indice BOOLEAN NOT NULL DEFAULT FALSE,
    es_clave_foranea BOOLEAN NOT NULL DEFAULT FALSE,
    tabla_referenciada VARCHAR(200),
    campo_referenciado VARCHAR(200),
    valores_posibles TEXT,
    ejemplos_valores TEXT,
    notas TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    orden INTEGER NOT NULL DEFAULT 0,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_definiciones_campos_id ON definiciones_campos (id);
CREATE INDEX IF NOT EXISTS ix_definiciones_campos_tabla ON definiciones_campos (tabla);
CREATE INDEX IF NOT EXISTS ix_definiciones_campos_campo ON definiciones_campos (campo);

-- actualizado_en: la aplicación (backend) lo actualiza en cada UPDATE; no hace falta trigger.
