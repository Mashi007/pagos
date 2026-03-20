# Implementación Mejorada: Notificaciones LIQUIDADO con PDF de Estado de Cuenta

## Resumen de cambios

Se ha mejorado el sistema de notificaciones para préstamos liquidados para que ahora **genere y adjunte automáticamente el PDF del estado de cuenta** de cada cliente a cada notificación de liquidación.

## Flujo completo

```
9 PM (21:00) - Trigger del Scheduler
    ↓
LiquidadoScheduler.actualizar_prestamos_liquidado()
    ↓
1. Identifica préstamos APROBADO con 100% de pagos
    ↓
2. Ejecuta: SELECT actualizar_prestamos_a_liquidado_automatico()
    ↓
3. Para cada préstamo liquidado:
    ├─ Obtiene datos del cliente (nombre, email, cédula)
    ├─ Genera PDF del estado de cuenta:
    │   ├─ Tabla de TODOS los préstamos del cliente (estado actual)
    │   ├─ Tabla de cuotas PENDIENTES del cliente
    │   └─ Total pendiente consolidado
    ├─ Construye correo HTML con:
    │   ├─ Saludo personalizado
    │   ├─ Confirmación del monto liquidado
    │   └─ Total pagado
    ├─ Adjunta PDF con nombre: estado_cuenta_{referencia}.pdf
    ├─ Envía correo vía SMTP (infraestructura existente)
    └─ Registra en tabla envio_notificacion con tipo='liquidado'
    ↓
4. Frontend muestra en tab ?tab=liquidados
```

## Archivos modificados

### 1. `backend/app/services/liquidado_notificacion_service.py` (MEJORADO)

**Cambios principales:**

- **Nueva importación de `generar_pdf_estado_cuenta`** desde `app.services.estado_cuenta_pdf`
- **Nuevo método estático `_generar_pdf_estado_cuenta(db, cliente_id)`** que:
  - Consulta datos del cliente (cédula, nombre, email)
  - Obtiene lista de todos los préstamos del cliente con su estado
  - Obtiene lista de cuotas PENDIENTES
  - Calcula total pendiente
  - Llama a `generar_pdf_estado_cuenta()` que retorna bytes del PDF
  - Maneja errores y retorna `None` si falla
  
- **Mejora en `crear_notificacion()`**:
  - Ahora genera el PDF del estado de cuenta
  - Construye correo con contenido textual más profesional
  - Usa `send_email()` con parámetro `attachments` para adjuntar PDF
  - Registra en `envio_notificacion` con toda la información
  - Logging detallado con prefijo `[LIQUIDADO_NOTIF]`

**Pseudocódigo mejorado:**

```python
def crear_notificacion(prestamo_id, capital, suma_pagado):
    db = SessionLocal()
    try:
        # Obtener cliente y email
        cliente_data = db.query("SELECT cliente_id, email, cedula, nombre FROM prestamos...")
        
        if not email:
            return False
        
        # NUEVO: Generar PDF
        pdf_bytes = _generar_pdf_estado_cuenta(db, cliente_id)
        
        # Preparar correo con adjunto
        asunto = f"Préstamo {referencia} - 100% Liquidado"
        cuerpo = f"Su préstamo por {capital:,.2f} ha sido pagado..."
        
        # NUEVO: Si se generó PDF, adjuntarlo
        adjuntos = None
        if pdf_bytes:
            adjuntos = [("estado_cuenta_{referencia}.pdf", pdf_bytes)]
        
        # Enviar con adjunto
        exito, error = send_email(
            to_emails=[email],
            subject=asunto,
            body_text=cuerpo,
            attachments=adjuntos,
            tipo_tab='liquidados'
        )
        
        # Registrar en auditoria
        db.insert(envio_notificacion, {
            prestamo_id, cliente_id, cedula, email, 
            tipo='liquidado', asunto, cuerpo, exito
        })
        
        return exito
    finally:
        db.close()
```

### 2. `backend/app/services/liquidado_scheduler.py` (ACTUALIZADO)

**Cambios principales:**

- **Importa `notificacion_service`** para llamar a `crear_notificacion()`
- **Nuevo código que:**
  - Identifica préstamos que van a ser liquidados ANTES de actualizar (obtiene capital y suma pagado)
  - Ejecuta la función PL/pgSQL de actualización
  - Itera sobre cada préstamo liquidado
  - Llama a `notificacion_service.crear_notificacion()` para generar y enviar notificación con PDF
  - Registra estadísticas (notificaciones exitosas vs fallidas)

**Pseudocódigo mejorado:**

```python
def actualizar_prestamos_liquidado():
    db = SessionLocal()
    try:
        logger.info("INICIANDO: Actualizacion de prestamos a LIQUIDADO")
        
        # NUEVO: Identificar prestamos a liquidar
        prestamos_liquidar = db.query("""
            SELECT p.id, p.total_financiamiento, 
                   COALESCE(SUM(c.monto_cuota WHERE c.estado='PAGADO'), 0)
            FROM prestamos p LEFT JOIN cuotas c
            WHERE p.estado='APROBADO'
            GROUP BY p.id
            HAVING SUM(c.monto_cuota) >= p.total_financiamiento - 0.01
        """)
        
        # Actualizar estados en BD
        db.execute("SELECT actualizar_prestamos_a_liquidado_automatico()")
        db.commit()
        
        # NUEVO: Generar notificaciones por cada prestamo
        notif_ok = 0
        notif_fail = 0
        for prestamo_id, capital, suma_pagado in prestamos_liquidar:
            try:
                exito = notificacion_service.crear_notificacion(
                    prestamo_id=prestamo_id,
                    capital=float(capital),
                    suma_pagado=float(suma_pagado)
                )
                if exito:
                    notif_ok += 1
                else:
                    notif_fail += 1
            except Exception as e:
                logger.error(f"Error generando notificacion: {e}")
                notif_fail += 1
        
        logger.info(f"Notificaciones: {notif_ok} exitosas, {notif_fail} fallidas")
```

## Ventajas de esta implementación

✅ **PDF profesional**: Usa la misma generación de PDF que el endpoint público, garantizando consistencia visual
✅ **Estado de cuenta completo**: Muestra todos los préstamos del cliente y cuotas pendientes
✅ **Adjunto automático**: No requiere intervención manual, se genera en tiempo de ejecución
✅ **Manejo de errores**: Si falla la generación de PDF, el correo se envía sin adjunto (fallback)
✅ **Auditoria completa**: Todo se registra en `envio_notificacion` para trazabilidad
✅ **Compatible con frontend**: El tipo `liquidados` ya existe en la UI
✅ **Usa infraestructura existente**: `send_email()` de `app.core.email` ya soporta adjuntos
✅ **Logging detallado**: Fácil debugging con prefijo `[LIQUIDADO_NOTIF]`

## Tabla `envio_notificacion`

Los registros se insertan con:

| Campo | Valor | Descripción |
|-------|-------|-------------|
| prestamo_id | {id} | ID del préstamo liquidado |
| cliente_id | {id} | ID del cliente |
| cedula | {cedula} | Cédula del cliente |
| email | {email} | Correo del cliente |
| tipo | `liquidado` | Tipo de notificación (visible en tab liquidados) |
| asunto | `Préstamo {ref} - 100% Liquidado` | Asunto del correo |
| cuerpo | {texto} | Contenido del correo (primeros 2000 chars) |
| exito | `true\|false` | Si se envió exitosamente |
| fecha_envio | `NOW()` | Timestamp del envío |

## Validación post-implementación

### 1. Verificar que la notificación se registra en BD

```sql
SELECT * FROM envio_notificacion 
WHERE tipo = 'liquidado' 
ORDER BY fecha_envio DESC 
LIMIT 10;
```

Esperado: Registros con `tipo='liquidado'` y `exito=true`

### 2. Verificar que el PDF se adjuntó

- Revisar logs de la aplicación por: `[LIQUIDADO_NOTIF] Enviando correo con PDF adjunto`
- Verificar el correo recibido tiene el PDF: `estado_cuenta_{referencia}.pdf`

### 3. Verificar en el frontend

- Navegar a: https://rapicredit.onrender.com/pagos/notificaciones?tab=liquidados
- Deberían aparecer notificaciones recientes del tipo "liquidado"

### 4. Trigger manual para testing (9 PM + 1 min)

```bash
# Si necesitas probar antes de las 9 PM, edita el scheduler:
# liquidado_scheduler.py: hour=21 -> hour=14 (2 PM)
# Luego reinicia la app y espera a las 14:00
```

## Notas de implementación

- El PDF se genera usando datos EN VIVO del cliente en el momento de liquidación
- Si el cliente tiene otros préstamos, aparecerán en el PDF con su estado actual
- Solo cuotas `PENDIENTE` aparecen en el PDF (cuotas ya pagadas no se muestran)
- Si hay error generando PDF, el correo se envía sin adjunto (graceful degradation)
- Cada liquidación genera UN correo (un PDF por préstamo liquidado)
- Los correos se envían a través de la infraestructura SMTP existente configurada en el dashboard

## Dependencias requeridas

Todas están ya instaladas en el proyecto:
- `reportlab` - para generar PDF
- `apscheduler` - para scheduler
- `sqlalchemy` - para consultas
- `fastapi` - framework web

No se requieren nuevas dependencias.
