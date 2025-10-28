-- ============================================
-- EJECUTAR MIGRACIÓN DE PLANTILLAS DE NOTIFICACIONES
-- ============================================

-- Crear tabla notificacion_plantillas
CREATE TABLE IF NOT EXISTS notificacion_plantillas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    tipo VARCHAR(20) NOT NULL,
    asunto VARCHAR(200) NOT NULL,
    cuerpo TEXT NOT NULL,
    variables_disponibles TEXT,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    zona_horaria VARCHAR(50) NOT NULL DEFAULT 'America/Caracas',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Crear índice
CREATE INDEX IF NOT EXISTS ix_notificacion_plantillas_id ON notificacion_plantillas(id);

-- Insertar las 7 plantillas iniciales
INSERT INTO notificacion_plantillas (nombre, descripcion, tipo, asunto, cuerpo, activa, zona_horaria) VALUES
(
    'Recordatorio - 5 Días Antes',
    'Notificación enviada 5 días antes del vencimiento de la cuota',
    'PAGO_5_DIAS_ANTES',
    'Recordatorio de Pago - Cuota {{numero_cuota}} - 5 días restantes',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2563eb; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9fafb; }
        .details { background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 RapiCredit</h1>
        </div>
        
        <div class="content">
            <h2>Recordatorio de Pago - 5 Días Restantes</h2>
            
            <p>Estimado/a <strong>{{nombre}}</strong>,</p>
            
            <p>Le recordamos que tiene un pago pendiente:</p>
            
            <div class="details">
                <p><strong>📋 Crédito ID:</strong> {{credito_id}}</p>
                <p><strong>💵 Cuota:</strong> {{numero_cuota}}</p>
                <p><strong>💰 Monto:</strong> {{monto}} VES</p>
                <p><strong>📅 Fecha de vencimiento:</strong> {{fecha_vencimiento}}</p>
            </div>
            
            <p>Por favor, realice su pago a tiempo.</p>
            
            <p>Saludos cordiales,<br><strong>Equipo RapiCredit</strong></p>
        </div>
        
        <div class="footer">
            <p>Este es un email automático, por favor no responda.</p>
            <p>© 2025 RapiCredit. Todos los derechos reservados.</p>
        </div>
    </div>
</body>
</html>',
    TRUE,
    'America/Caracas'
),
(
    'Recordatorio - 3 Días Antes',
    'Notificación enviada 3 días antes del vencimiento de la cuota',
    'PAGO_3_DIAS_ANTES',
    'Recordatorio de Pago - Cuota {{numero_cuota}} - 3 días restantes',
    'Estimado/a {{nombre}}, le recordamos que el pago de {{monto}} VES (Cuota {{numero_cuota}}) vence en 3 días ({{fecha_vencimiento}}). Por favor, realice su pago a tiempo.',
    TRUE,
    'America/Caracas'
),
(
    'Recordatorio - 1 Día Antes',
    'Notificación enviada 1 día antes del vencimiento de la cuota',
    'PAGO_1_DIA_ANTES',
    'Recordatorio Urgente - Cuota {{numero_cuota}} vence mañana',
    'Estimado/a {{nombre}}, le recordamos que el pago de {{monto}} VES (Cuota {{numero_cuota}}) VENCE MAÑANA ({{fecha_vencimiento}}). Por favor, realice su pago a tiempo.',
    TRUE,
    'America/Caracas'
),
(
    'Recordatorio - Día de Vencimiento',
    'Notificación enviada el día de vencimiento de la cuota',
    'PAGO_DIA_0',
    'Recordatorio Urgente - Cuota {{numero_cuota}} vence HOY',
    'Estimado/a {{nombre}}, le recordamos que el pago de {{monto}} VES (Cuota {{numero_cuota}}) VENCE HOY ({{fecha_vencimiento}}). Por favor, realice su pago inmediatamente.',
    TRUE,
    'America/Caracas'
),
(
    'Alerta - 1 Día Atrasado',
    'Notificación enviada 1 día después del vencimiento',
    'PAGO_1_DIA_ATRASADO',
    'Alerta - Cuota {{numero_cuota}} vencida (1 día de atraso)',
    'Estimado/a {{nombre}}, le informamos que el pago de {{monto}} VES (Cuota {{numero_cuota}}) tiene 1 día de atraso. Por favor, realice su pago para evitar cargos adicionales.',
    TRUE,
    'America/Caracas'
),
(
    'Alerta - 3 Días Atrasado',
    'Notificación enviada 3 días después del vencimiento',
    'PAGO_3_DIAS_ATRASADO',
    'Alerta - Cuota {{numero_cuota}} vencida (3 días de atraso)',
    'Estimado/a {{nombre}}, le informamos que el pago de {{monto}} VES (Cuota {{numero_cuota}}) tiene 3 días de atraso. Es importante que realice su pago.',
    TRUE,
    'America/Caracas'
),
(
    'Alerta - 5 Días Atrasado',
    'Notificación enviada 5 días después del vencimiento',
    'PAGO_5_DIAS_ATRASADO',
    'Alerta Urgente - Cuota {{numero_cuota}} vencida (5 días de atraso)',
    'Estimado/a {{nombre}}, le informamos que el pago de {{monto}} VES (Cuota {{numero_cuota}}) tiene 5 días de atraso. Es urgente que realice su pago para evitar mayores cargos.',
    TRUE,
    'America/Caracas'
);

-- Verificar que se crearon correctamente
SELECT 
    id, 
    nombre, 
    tipo, 
    activa,
    zona_horaria
FROM notificacion_plantillas
ORDER BY tipo;

