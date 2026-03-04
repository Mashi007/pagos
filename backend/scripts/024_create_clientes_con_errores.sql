-- Migración 024: Crear tabla clientes_con_errores para carga masiva
-- Tabla para almacenar clientes que no pasaron validación en carga desde Excel

CREATE TABLE IF NOT EXISTS public.clientes_con_errores (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20),
    nombres VARCHAR(100),
    telefono VARCHAR(100),
    email VARCHAR(100),
    direccion TEXT,
    fecha_nacimiento VARCHAR(50),
    ocupacion VARCHAR(100),
    estado VARCHAR(30) DEFAULT 'PENDIENTE',
    errores_descripcion TEXT,
    observaciones TEXT,
    fila_origen INTEGER,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_registro VARCHAR(255)
);

-- Índices para búsquedas frecuentes
CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_cedula ON public.clientes_con_errores(cedula);
CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_email ON public.clientes_con_errores(email);
CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_estado ON public.clientes_con_errores(estado);
CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_fecha ON public.clientes_con_errores(fecha_registro DESC);

-- Verificación
SELECT COUNT(*) as tabla_creada FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'clientes_con_errores';
