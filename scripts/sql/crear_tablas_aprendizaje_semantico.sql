-- ============================================
-- Crear Tablas para Aprendizaje Semántico AI
-- ============================================

-- Tabla: ai_diccionario_semantico
-- Almacena palabras y definiciones para entrenar al AI
CREATE TABLE IF NOT EXISTS ai_diccionario_semantico (
    id SERIAL PRIMARY KEY,
    palabra VARCHAR(200) NOT NULL UNIQUE,
    definicion TEXT NOT NULL,
    categoria VARCHAR(100),
    campo_relacionado VARCHAR(100),
    tabla_relacionada VARCHAR(100),
    sinonimos TEXT, -- JSON array
    ejemplos_uso TEXT, -- JSON array
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    orden INTEGER DEFAULT 0,
    creado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_ai_diccionario_semantico_palabra ON ai_diccionario_semantico(palabra);
CREATE INDEX IF NOT EXISTS idx_ai_diccionario_semantico_categoria ON ai_diccionario_semantico(categoria);
CREATE INDEX IF NOT EXISTS idx_ai_diccionario_semantico_activo ON ai_diccionario_semantico(activo);

-- Tabla: ai_definiciones_campos
-- Almacena definiciones de campos de BD para entrenar acceso rápido
CREATE TABLE IF NOT EXISTS ai_definiciones_campos (
    id SERIAL PRIMARY KEY,
    tabla VARCHAR(100) NOT NULL,
    campo VARCHAR(100) NOT NULL,
    definicion TEXT NOT NULL,
    tipo_dato VARCHAR(50),
    es_obligatorio BOOLEAN NOT NULL DEFAULT FALSE,
    tiene_indice BOOLEAN NOT NULL DEFAULT FALSE,
    es_clave_foranea BOOLEAN NOT NULL DEFAULT FALSE,
    tabla_referenciada VARCHAR(100),
    campo_referenciado VARCHAR(100),
    valores_posibles TEXT, -- JSON array
    ejemplos_valores TEXT, -- JSON array
    notas TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    orden INTEGER DEFAULT 0,
    creado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(tabla, campo)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_ai_definiciones_campos_tabla ON ai_definiciones_campos(tabla);
CREATE INDEX IF NOT EXISTS idx_ai_definiciones_campos_campo ON ai_definiciones_campos(campo);
CREATE INDEX IF NOT EXISTS idx_ai_definiciones_campos_activo ON ai_definiciones_campos(activo);

-- Comentarios
COMMENT ON TABLE ai_diccionario_semantico IS 'Diccionario semántico: palabras y definiciones para entrenar al AI';
COMMENT ON TABLE ai_definiciones_campos IS 'Definiciones de campos de BD para entrenar acceso rápido';

COMMENT ON COLUMN ai_diccionario_semantico.sinonimos IS 'JSON array de sinónimos: ["sinónimo1", "sinónimo2"]';
COMMENT ON COLUMN ai_diccionario_semantico.ejemplos_uso IS 'JSON array de ejemplos: ["ejemplo1", "ejemplo2"]';
COMMENT ON COLUMN ai_definiciones_campos.valores_posibles IS 'JSON array de valores posibles: ["valor1", "valor2"]';
COMMENT ON COLUMN ai_definiciones_campos.ejemplos_valores IS 'JSON array de ejemplos: ["ejemplo1", "ejemplo2"]';

-- ============================================
-- Tabla: ai_calificaciones_chat
-- Almacena calificaciones (pulgar arriba/abajo) de respuestas del Chat AI
-- ============================================

CREATE TABLE IF NOT EXISTS ai_calificaciones_chat (
    id SERIAL PRIMARY KEY,
    pregunta TEXT NOT NULL,
    respuesta_ai TEXT NOT NULL,
    calificacion VARCHAR(20) NOT NULL, -- 'arriba' o 'abajo'
    usuario_email VARCHAR(255),
    procesado BOOLEAN NOT NULL DEFAULT FALSE,
    notas_procesamiento TEXT,
    mejorado BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_ai_calificaciones_chat_calificacion ON ai_calificaciones_chat(calificacion);
CREATE INDEX IF NOT EXISTS idx_ai_calificaciones_chat_usuario_email ON ai_calificaciones_chat(usuario_email);
CREATE INDEX IF NOT EXISTS idx_ai_calificaciones_chat_procesado ON ai_calificaciones_chat(procesado);
CREATE INDEX IF NOT EXISTS idx_ai_calificaciones_chat_creado_en ON ai_calificaciones_chat(creado_en);

-- Comentarios
COMMENT ON TABLE ai_calificaciones_chat IS 'Calificaciones de respuestas del Chat AI (pulgar arriba/abajo)';
COMMENT ON COLUMN ai_calificaciones_chat.calificacion IS 'Calificación: "arriba" o "abajo"';
COMMENT ON COLUMN ai_calificaciones_chat.procesado IS 'Si la calificación negativa ya fue procesada para mejorar el sistema';
COMMENT ON COLUMN ai_calificaciones_chat.notas_procesamiento IS 'Notas sobre cómo se procesó esta calificación';
COMMENT ON COLUMN ai_calificaciones_chat.mejorado IS 'Si el sistema fue mejorado basado en esta calificación';
