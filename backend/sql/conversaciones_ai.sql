-- conversaciones_ai (entrenamiento AI - Fine-tuning)
-- PostgreSQL. Ejecutar una vez.

SET client_min_messages = WARNING;

CREATE TABLE IF NOT EXISTS conversaciones_ai (
    id SERIAL PRIMARY KEY,
    pregunta TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    contexto_usado TEXT,
    documentos_usados TEXT,
    modelo_usado VARCHAR(100),
    tokens_usados INTEGER,
    tiempo_respuesta INTEGER,
    calificacion INTEGER,
    feedback TEXT,
    usuario_id INTEGER,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_conversaciones_ai_id ON conversaciones_ai (id);
CREATE INDEX IF NOT EXISTS ix_conversaciones_ai_calificacion ON conversaciones_ai (calificacion);
