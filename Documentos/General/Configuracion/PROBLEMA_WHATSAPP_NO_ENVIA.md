# 🔴 Problema: WhatsApp No Envía Mensajes Automáticamente

## 📋 Diagnóstico del Problema

### ❌ **Problema Principal**

El scheduler automático **SOLO envía EMAIL**, no envía WhatsApp. Todos los jobs del scheduler están hardcodeados para usar `canal="EMAIL"`.

### 🔍 **Evidencia en el Código**

En `backend/app/core/scheduler.py`, todos los jobs crean notificaciones con:

```python
nueva_notif = Notificacion(
    cliente_id=cliente_id,
    tipo=tipo_notificacion,
    canal="EMAIL",  # ❌ SIEMPRE EMAIL, nunca WHATSAPP
    asunto=asunto,
    mensaje=cuerpo,
    estado="PENDIENTE",
)
```

**Ubicaciones donde ocurre:**
- Línea 205: `calcular_notificaciones_previas_job()`
- Línea 358: `calcular_notificaciones_dia_pago_job()`
- Línea 525: `calcular_notificaciones_retrasadas_job()`
- Línea 693: `calcular_notificaciones_prejudiciales_job()`

---

## ⚠️ **Problemas Adicionales Detectados**

### 1. **Modo Pruebas Activo**

Según los logs anteriores:
- `modo_pruebas: 'true'` (activo)
- `telefono_pruebas: '+593983000700'` (configurado)

**Impacto**: Si el scheduler enviara WhatsApp, todos los mensajes se redirigirían al número de pruebas `+593983000700` en lugar de a los clientes reales.

### 2. **Jobs Programados a las 4:00 AM**

Los jobs se ejecutan a las 4:00 AM diariamente. Si no hay logs de ejecución, puede ser que:
- Los jobs no se hayan ejecutado aún (esperar a las 4 AM)
- Los jobs se ejecutaron pero solo enviaron EMAIL

---

## ✅ **Soluciones Posibles**

### **Opción 1: Modificar Scheduler para Enviar WhatsApp También** (Recomendado)

Modificar los jobs del scheduler para que envíen tanto EMAIL como WhatsApp cuando esté disponible.

**Ventajas:**
- Los clientes recibirán notificaciones por ambos canales
- Mejor cobertura de comunicación
- No requiere cambios en la configuración

**Desventajas:**
- Requiere modificar el código del scheduler
- Puede aumentar el costo de envíos

### **Opción 2: Configuración de Canal Preferido**

Agregar una configuración que permita elegir el canal preferido (EMAIL, WHATSAPP, o AMBOS).

**Ventajas:**
- Flexibilidad para elegir el canal
- Configurable sin cambiar código

**Desventajas:**
- Requiere implementar lógica de selección de canal
- Requiere interfaz de configuración

### **Opción 3: Envío Dual Automático**

Enviar por ambos canales automáticamente si están configurados.

**Ventajas:**
- Máxima cobertura
- No requiere configuración adicional

**Desventajas:**
- Puede ser costoso si se envían muchos mensajes
- Puede ser redundante para algunos clientes

---

## 🔧 **Implementación Recomendada: Opción 1**

### Cambios Necesarios en `scheduler.py`:

1. **Agregar lógica para enviar WhatsApp además de Email**
2. **Verificar si WhatsApp está configurado antes de enviar**
3. **Respetar el modo de pruebas**
4. **Manejar errores de WhatsApp sin afectar el envío de Email**

### Estructura Propuesta:

```python
# Después de enviar Email exitosamente:
if resultado_email.get("success"):
    nueva_notif.estado = "ENVIADA"
    nueva_notif.enviada_en = datetime.utcnow()
    nueva_notif.respuesta_servicio = resultado_email.get("message", "Email enviado exitosamente")
    enviadas += 1
    
    # ✅ AGREGAR: Enviar también por WhatsApp si está disponible
    if cliente.telefono:
        try:
            from app.services.whatsapp_service import WhatsAppService
            whatsapp_service = WhatsAppService(db=db)
            
            # Crear notificación WhatsApp
            notif_whatsapp = Notificacion(
                cliente_id=cliente_id,
                tipo=tipo_notificacion,
                canal="WHATSAPP",
                asunto=asunto,
                mensaje=cuerpo,
                estado="PENDIENTE",
            )
            db.add(notif_whatsapp)
            db.commit()
            db.refresh(notif_whatsapp)
            
            # Enviar WhatsApp
            resultado_whatsapp = await whatsapp_service.send_message(
                to_number=str(cliente.telefono),
                message=cuerpo,
            )
            
            if resultado_whatsapp.get("success"):
                notif_whatsapp.estado = "ENVIADA"
                notif_whatsapp.enviada_en = datetime.utcnow()
                logger.info(f"✅ WhatsApp enviado a {cliente.telefono} (Cliente {cliente_id})")
            else:
                notif_whatsapp.estado = "FALLIDA"
                notif_whatsapp.error_mensaje = resultado_whatsapp.get("message", "Error desconocido")
                logger.warning(f"⚠️ Error enviando WhatsApp a {cliente.telefono}: {resultado_whatsapp.get('message')}")
            
            db.commit()
        except Exception as e:
            logger.error(f"❌ Error enviando WhatsApp: {e}")
            db.rollback()
```

---

## 📋 **Checklist de Verificación**

### Antes de Implementar:

- [ ] Verificar que WhatsApp esté correctamente configurado
- [ ] Verificar que el Access Token no haya expirado
- [ ] Decidir si usar modo Producción o Pruebas
- [ ] Si modo Pruebas: Verificar que el teléfono de pruebas sea correcto

### Después de Implementar:

- [ ] Probar envío manual de WhatsApp
- [ ] Verificar que los jobs del scheduler envíen WhatsApp
- [ ] Revisar logs para confirmar envíos
- [ ] Verificar que los mensajes lleguen correctamente

---

## ⚠️ **Notas Importantes**

1. **Modo Pruebas**: Si `modo_pruebas: 'true'`, todos los mensajes WhatsApp se redirigen al `telefono_pruebas`. Para enviar a clientes reales, cambiar a `modo_pruebas: 'false'`.

2. **Rate Limits de Meta**: 
   - 1,000 mensajes por día (nivel gratuito)
   - 80 mensajes por segundo
   - El sistema maneja estos límites automáticamente

3. **Costo**: Enviar por WhatsApp puede tener costos según el plan de Meta. Verificar límites y costos antes de activar envíos masivos.

4. **Horario de Ejecución**: Los jobs se ejecutan a las 4:00 AM. Para probar antes, se puede ejecutar manualmente o cambiar temporalmente la hora.

---

## 🚀 **Próximos Pasos**

1. **Decidir qué solución implementar** (recomendado: Opción 1)
2. **Modificar el scheduler** para incluir envío de WhatsApp
3. **Probar en modo Pruebas** primero
4. **Cambiar a modo Producción** cuando esté listo
5. **Monitorear logs y envíos** para verificar funcionamiento

