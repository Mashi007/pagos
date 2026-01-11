# 📊 Análisis de Logs del Servidor Backend

**Fecha**: 2026-01-11  
**Servicio**: pagos-backend  
**Plataforma**: Render

## 🔍 Resumen Ejecutivo

Los logs muestran que el servidor backend se está iniciando correctamente pero recibiendo señales de shutdown aproximadamente 1 minuto después de iniciarse, causando reinicios frecuentes. También se observan mensajes duplicados del scheduler.

## 📋 Análisis de los Logs

### Patrón Observado

```
17:24:04 - Scheduler iniciado correctamente
17:24:04 - Jobs agregados y programados
17:24:04 - Application startup complete
17:24:04 - Health check HEAD request (127.0.0.1)
17:25:12 - Shutting down (aprox. 1 minuto después del inicio)
17:25:13 - Scheduler detenido correctamente
17:25:13 - Application shutdown complete
```

### Observaciones Clave

1. ✅ **Inicio Correcto**: El servidor inicia sin errores
2. ✅ **Scheduler Funcional**: El scheduler se inicia y programa jobs correctamente
3. ⚠️ **Logs Duplicados**: Los mensajes del scheduler aparecen duplicados
4. ⚠️ **Reinicios Frecuentes**: El servidor recibe shutdown aproximadamente cada minuto
5. ✅ **Shutdown Graceful**: El servidor se cierra correctamente con cleanup

## 🔍 Posibles Causas

### 1. Health Check de Render
Render hace health checks periódicos. Si el health check falla o tarda demasiado, Render puede reiniciar el servicio.

### 2. Plan Gratuito de Render
Los servicios en el plan gratuito pueden tener límites de tiempo de ejecución o reiniciarse después de períodos de inactividad.

### 3. Configuración de Timeout
Render puede tener timeouts configurados que causan reinicios si el servicio no responde en el tiempo esperado.

### 4. Múltiples Workers
Aunque está configurado con `--workers 1`, podría haber algún problema con la inicialización que cause logs duplicados.

## ✅ Mejoras Implementadas

### 1. Logging Optimizado del Scheduler
- **Antes**: Los mensajes de jobs programados se mostraban siempre, incluso si el scheduler ya estaba corriendo
- **Después**: Los mensajes de jobs solo se muestran cuando el scheduler se inicia por primera vez
- **Impacto**: Reduce logs duplicados y mejora la claridad

```python
# Solo loggear jobs programados una vez cuando se inicia el scheduler
if not scheduler.running:
    scheduler.start()
    logger.info("✅ Scheduler iniciado correctamente")
    # ... logs de jobs programados ...
else:
    logger.debug("✅ Scheduler ya estaba corriendo, omitiendo logs de jobs")
```

### 2. Logging Mejorado para Diagnóstico
- **Agregado**: Timestamp de inicio y cierre del servidor
- **Agregado**: Tiempo de ejecución (uptime) antes del cierre
- **Impacto**: Facilita identificar patrones de reinicio y diagnosticar problemas

```python
startup_time = time.time()
startup_timestamp = datetime.now().isoformat()
logger.info(f"🚀 Iniciando aplicación - Timestamp: {startup_timestamp}")

# ... al shutdown ...
uptime_seconds = shutdown_time - startup_time
logger.info(f"⏱️  Tiempo de ejecución: {uptime_seconds:.1f} segundos")
```

### 3. Shutdown Graceful Mejorado
- **Mejorado**: Logging más detallado durante el shutdown
- **Agregado**: Información de tiempo de ejecución antes del cierre
- **Impacto**: Facilita diagnosticar por qué el servidor se está cerrando

## 📊 Métricas Esperadas

Después de las mejoras, deberías ver:

1. **Logs sin duplicación**: Los mensajes del scheduler solo aparecen una vez
2. **Mejor diagnóstico**: Logs muestran tiempo de ejecución antes de cada reinicio
3. **Shutdown informativo**: Logs detallados durante el proceso de cierre

## 🔧 Recomendaciones Adicionales

### 1. Verificar Configuración en Render Dashboard
- Revisar si hay límites de tiempo de ejecución configurados
- Verificar la configuración del health check path (`/api/v1/health/render`)
- Revisar los logs de Render para ver si hay errores de health check

### 2. Monitorear Uptime
Con el nuevo logging, podrás ver exactamente cuánto tiempo el servidor está ejecutándose antes de recibir shutdown. Esto ayudará a identificar si:
- Es un problema de configuración de Render
- Es un problema de recursos (memoria/CPU)
- Es un comportamiento esperado del plan gratuito

### 3. Verificar Health Check Endpoint
Asegúrate de que el endpoint `/api/v1/health/render` responda rápidamente:
```bash
curl https://pagos-f2qf.onrender.com/api/v1/health/render
```

### 4. Considerar Upgrade del Plan
Si los reinicios frecuentes afectan la experiencia del usuario, considera:
- Upgrade a un plan de pago con mejor disponibilidad
- Configurar auto-scaling si es necesario

## 📝 Próximos Pasos

1. ✅ **Completado**: Optimizar logging del scheduler
2. ✅ **Completado**: Mejorar logging para diagnóstico
3. ✅ **Completado**: Agregar información de uptime al shutdown
4. ⏳ **Pendiente**: Monitorear logs después del próximo deploy
5. ⏳ **Pendiente**: Verificar si los reinicios persisten con las mejoras

## 🔗 Referencias

- [Render Health Checks Documentation](https://render.com/docs/health-checks)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
