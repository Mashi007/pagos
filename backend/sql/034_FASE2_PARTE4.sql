-- ============================================================================
-- FASE 2 PARTE 4: Cachés en BD
-- ============================================================================

DROP TABLE IF EXISTS adjuntos_fijos_cache CASCADE;

CREATE TABLE adjuntos_fijos_cache (
    id SERIAL PRIMARY KEY,
    caso VARCHAR(100) NOT NULL UNIQUE,
    contenido BYTEA NOT NULL,
    nombre_archivo VARCHAR(255),
    tamaño_bytes BIGINT,
    hash_contenido VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_adjuntos_fijos_cache_caso 
ON adjuntos_fijos_cache (caso);

DROP TABLE IF EXISTS email_config_cache CASCADE;

CREATE TABLE email_config_cache (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB,
    servicio VARCHAR(50),
    hash_value VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '15 minutes'
);

CREATE INDEX idx_email_config_cache_key 
ON email_config_cache (config_key);

-- Verificar
SELECT COUNT(*) as adjuntos FROM adjuntos_fijos_cache;
SELECT COUNT(*) as configs FROM email_config_cache;
