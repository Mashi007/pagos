-- Migración 025: Crear tabla prestamos_con_errores para carga masiva
-- Tabla para almacenar préstamos que no pasaron validación en carga desde Excel

CREATE TABLE IF NOT EXISTS public.prestamos_con_errores (
    id SERIAL PRIMARY KEY,
    cedula_cliente VARCHAR(20),
    total_financiamiento NUMERIC(14, 2),
    modalidad_pago VARCHAR(50),
    numero_cuotas INTEGER,
    producto VARCHAR(255),
    analista VARCHAR(255),
    concesionario VARCHAR(255),
    estado VARCHAR(30) DEFAULT 'PENDIENTE',
    errores_descripcion TEXT,
    observaciones TEXT,
    fila_origen INTEGER,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_registro VARCHAR(255)
);

-- Índices para búsquedas frecuentes
CREATE INDEX IF NOT EXISTS idx_prestamos_con_errores_cedula ON public.prestamos_con_errores(cedula_cliente);
CREATE INDEX IF NOT EXISTS idx_prestamos_con_errores_estado ON public.prestamos_con_errores(estado);
CREATE INDEX IF NOT EXISTS idx_prestamos_con_errores_fecha ON public.prestamos_con_errores(fecha_registro DESC);

-- Verificación
SELECT COUNT(*) as tabla_creada FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'prestamos_con_errores';
