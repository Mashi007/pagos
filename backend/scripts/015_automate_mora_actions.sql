-- Migración 015: Crear trigger para automtización de cobranza a 91 días
-- [MORA] Cuando una cuota pasa a estado MORA (>90 días sin pago), se puede marcar para acciones de cobranza

-- 1. Crear tabla de seguimiento para cuotas en mora
CREATE TABLE IF NOT EXISTS public.cuotas_en_mora (
    id BIGSERIAL PRIMARY KEY,
    cuota_id INTEGER NOT NULL UNIQUE,
    prestamo_id INTEGER NOT NULL,
    cliente_id INTEGER,
    fecha_ingreso_mora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dias_mora_actual INTEGER,
    accion_cobranza VARCHAR(50),
    fecha_accion TIMESTAMP,
    notificacion_enviada BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (cuota_id) REFERENCES public.cuotas(id) ON DELETE CASCADE,
    FOREIGN KEY (prestamo_id) REFERENCES public.prestamos(id) ON DELETE CASCADE
);

-- 2. Crear función PL/pgSQL para detectar cuotas que entran en mora
CREATE OR REPLACE FUNCTION public.detectar_cuotas_en_mora()
RETURNS TABLE (cuota_id integer, dias_mora integer, estado text)
LANGUAGE SQL
AS $$
    SELECT 
        c.id,
        (CURRENT_DATE - c.fecha_vencimiento) as dias_mora,
        'MORA' as estado
    FROM public.cuotas c
    WHERE c.estado != 'PAGADO'
      AND (CURRENT_DATE - c.fecha_vencimiento) > 90
      AND c.id NOT IN (SELECT cuota_id FROM public.cuotas_en_mora)
$$;

-- 3. Vista para cuotas activas en mora (sin acción aún)
CREATE OR REPLACE VIEW public.cuotas_mora_activa AS
    SELECT 
        c.id,
        c.prestamo_id,
        c.numero_cuota,
        c.cliente_id,
        c.monto_cuota,
        c.fecha_vencimiento,
        (CURRENT_DATE - c.fecha_vencimiento) as dias_mora,
        c.total_pagado,
        cem.fecha_ingreso_mora,
        cem.accion_cobranza,
        cem.notificacion_enviada
    FROM public.cuotas c
    LEFT JOIN public.cuotas_en_mora cem ON c.id = cem.cuota_id
    WHERE c.estado = 'MORA'
      AND (CURRENT_DATE - c.fecha_vencimiento) > 90
    ORDER BY (CURRENT_DATE - c.fecha_vencimiento) DESC;

-- 4. Documentación de acciones automáticas a los 91 días:
-- - Generar alerta en dashboard
-- - Registrar en cuotas_en_mora para seguimiento
-- - Disparar notificación al cliente (SMS/email)
-- - Asignar a gestor de cobranza
