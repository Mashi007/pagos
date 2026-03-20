# Guía Final: Implementación de Notificaciones LIQUIDADO con PDF de Estado de Cuenta

## Estado de la implementación

✅ **COMPLETADO** - El sistema está listo para usar

### Cambios realizados

#### 1. Servicio de Notificación Mejorado
**Archivo:** `backend/app/services/liquidado_notificacion_service.py`

**Mejoras:**
- Genera PDF del estado de cuenta del cliente usando la misma funcionalidad que el endpoint público
- Adjunta automáticamente el PDF al correo de notificación
- PDF incluye:
  - Tabla de todos los préstamos del cliente (con estado actual)
  - Tabla de cuotas pendientes consolidadas
  - Total adeudado
  - Logo y diseño profesional de RapiCredit
  
- Fallback graceful: si falla la generación de PDF, el correo se envía sin adjunto

#### 2. Scheduler Mejorado  
**Archivo:** `backend/app/services/liquidado_scheduler.py`

**Mejoras:**
- Ejecuta diariamente a las 9 PM (21:00)
- Identifica préstamos que se van a liquidar
- Para cada préstamo liquidado, llama al servicio de notificación
- Registra estadísticas (notificaciones exitosas vs fallidas)
- Logging detallado para debugging

## Flujo de ejecución (9 PM cada noche)

```
┌─ Scheduler dispara actualizar_prestamos_liquidado()
│
├─ Busca prestamos APROBADO con 100% pagado
│
├─ Ejecuta: actualizar_prestamos_a_liquidado_automatico() en BD
│  ├─ Actualiza estado a LIQUIDADO
│  └─ Registra en auditoria_cambios_estado_prestamo
│
└─ Para cada prestamo liquidado:
   ├─ Consulta datos del cliente (nombre, email, cedula)
   │
   ├─ Genera PDF del estado de cuenta:
   │  ├─ Obtiene todos los prestamos del cliente
   │  ├─ Obtiene cuotas PENDIENTES
   │  └─ Calcula total pendiente
   │
   ├─ Construye correo HTML profesional:
   │  ├─ Saludo personalizado
   │  ├─ Confirmación de liquidacion
   │  └─ Total pagado
   │
   ├─ Adjunta: estado_cuenta_{referencia}.pdf
   │
   ├─ Envía vía SMTP (infraestructura existente)
   │
   └─ Registra en envio_notificacion con tipo='liquidado'
      └─ Visible en frontend: ?tab=liquidados
```

## Próximos pasos para validar

### 1. Reiniciar la aplicación

En la terminal del backend, ejecuta:

```bash
uvicorn app.main:app --reload
```

Deberías ver en los logs al startup:
```
INFO: Scheduler iniciado. Job programado para las 21:00 (9 PM) diariamente
```

### 2. Verificar logs de integración

Busca en los logs de la app al iniciarse:
```
[LIQUIDADO_NOTIF] ... inicializado
```

### 3. Testing manual (opcional)

Si quieres probar antes de las 9 PM:

**Opción A: Cambiar hora del scheduler (testing)**
```python
# backend/app/services/liquidado_scheduler.py, línea ~51
# Cambiar:
# hour=21,     (9 PM)
# a:
# hour=14,     (2 PM, solo para testing)
```

Luego reinicia la app y espera a las 14:00.

**Opción B: Trigger manual via API**
```bash
curl -X POST http://localhost:8000/api/v1/prestamos/actualizar-liquidado-manual \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Validar en la Base de Datos

```sql
-- Ver notificaciones liquidado recientes
SELECT 
  prestamo_id, 
  cliente_id, 
  email, 
  tipo, 
  asunto, 
  exito, 
  fecha_envio
FROM envio_notificacion 
WHERE tipo = 'liquidado' 
ORDER BY fecha_envio DESC 
LIMIT 10;
```

Esperado: Registros con `tipo='liquidado'` y `exito=true`

### 5. Validar en el Frontend

Navega a:
```
https://rapicredit.onrender.com/pagos/notificaciones?tab=liquidados
```

Deberías ver:
- Notificaciones recientes de tipo "LIQUIDADO"
- Cada notificacion muestra: Préstamo {ID} - 100% Liquidado

### 6. Verificar correo recibido

El cliente recibe un correo con:
- Asunto: `Préstamo {referencia} - 100% Liquidado`
- Cuerpo: Confirmación de liquidacion con montos
- **Adjunto: `estado_cuenta_{referencia}.pdf`** ← Este es el nuevo cambio

## Estructura de notificación en BD

```sql
-- Campo: tipo
-- Valores existentes: 'llamada', 'sms', 'email', 'reporte', etc.
-- Nuevo valor: 'liquidado' ← nuestro tipo

-- Ejemplo de registro:
INSERT INTO envio_notificacion (
  prestamo_id, 
  cliente_id, 
  cedula, 
  email, 
  tipo,              -- 'liquidado'
  asunto, 
  cuerpo, 
  exito,             -- true si se envió
  fecha_envio        -- NOW()
) VALUES (
  123,
  45,
  '1234567890',
  'cliente@example.com',
  'liquidado',
  'Préstamo ABC123 - 100% Liquidado',
  'Su préstamo ha sido completamente pagado...',
  true,
  NOW()
);
```

## Troubleshooting

### Problema: El PDF no se adjunta al correo

**Causas posibles:**
1. La función `generar_pdf_estado_cuenta()` falla silenciosamente
2. El cliente no tiene email registrado
3. Error de permisos al escribir el PDF en memoria

**Solución:**
- Revisar logs con: `[LIQUIDADO_NOTIF] Error generando PDF`
- Verificar que `reportlab` está instalado: `pip list | grep reportlab`
- Verificar email del cliente: `SELECT * FROM clientes WHERE id = {cliente_id}`

### Problema: Las notificaciones no se generan a las 9 PM

**Causas posibles:**
1. Scheduler no se inició correctamente
2. No hay préstamos para liquidar en ese momento
3. Error de timezone en el servidor

**Solución:**
- Revisar log de startup: `Scheduler iniciado`
- Revisar si hay préstamos APROBADO con 100% pagado en ese momento
- Ver logs detallados: `[LIQUIDADO_NOTIF] Iniciando generacion de notificaciones`

### Problema: Correo sin adjunto pero se registró en BD

**Comportamiento esperado** - Es intencional (fallback graceful)

El correo se envía sin PDF si:
- Falla la generación del PDF
- El cliente no tiene email
- Error en `send_email()`

Pero se registra en `envio_notificacion` para auditoria con `exito=true/false`

## Detalles técnicos

### Importaciones utilizadas
```python
from app.services.estado_cuenta_pdf import generar_pdf_estado_cuenta  # PDF profesional
from app.core.email import send_email  # Envío con adjuntos
from app.services.cuota_estado import estado_cuota_para_mostrar  # Estados legibles
```

### Función clave: `_generar_pdf_estado_cuenta(db, cliente_id)`

```python
def _generar_pdf_estado_cuenta(db: Session, cliente_id: int) -> Optional[bytes]:
    """
    Retorna: bytes del PDF o None si hay error
    Consulta en vivo: prestamos y cuotas del cliente
    Diseño: Mismo que endpoint público (consistencia visual)
    """
```

### Parámetros de `send_email()`

```python
send_email(
    to_emails=['cliente@example.com'],
    subject='...',
    body_text='...',
    attachments=[                          # NUEVO
        ('estado_cuenta_ABC123.pdf', pdf_bytes)
    ],
    tipo_tab='liquidados'                  # Para registrar en BD
)
```

## Configuración requerida

✅ Todas las dependencias ya están instaladas:
- `reportlab` - para PDF
- `apscheduler` - para scheduler  
- `sqlalchemy` - para BD
- `fastapi` - framework

No requiere instalación adicional.

## Rollback (si es necesario)

Si necesitas revertir a la versión anterior sin PDF:

1. Revertir archivos:
```bash
git checkout app/services/liquidado_notificacion_service.py
git checkout app/services/liquidado_scheduler.py
```

2. Reiniciar app

Nota: Las notificaciones seguirán registrándose en BD, solo que sin PDF adjunto.

## Contacto y soporte

- **Logs:** Busca `[LIQUIDADO_NOTIF]` en los logs de la app
- **Auditoria:** Consulta `envio_notificacion` donde `tipo='liquidado'`
- **Validación:** Ejecuta `python validar_integracion_pdf.py` en backend/
