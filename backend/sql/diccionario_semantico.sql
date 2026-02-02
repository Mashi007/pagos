-- diccionario_semantico (Configuración > AI > Diccionario semántico)
-- PostgreSQL. Ejecutar una vez.

SET client_min_messages = WARNING;

CREATE TABLE IF NOT EXISTS diccionario_semantico (
    id SERIAL PRIMARY KEY,
    palabra VARCHAR(200) NOT NULL,
    definicion TEXT NOT NULL,
    categoria VARCHAR(100),
    campo_relacionado VARCHAR(200),
    tabla_relacionada VARCHAR(200),
    sinonimos TEXT,
    ejemplos_uso TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    orden INTEGER NOT NULL DEFAULT 0,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_diccionario_semantico_id ON diccionario_semantico (id);
CREATE INDEX IF NOT EXISTS ix_diccionario_semantico_palabra ON diccionario_semantico (palabra);
CREATE INDEX IF NOT EXISTS ix_diccionario_semantico_categoria ON diccionario_semantico (categoria);
