# ⚙️ CONFIGURACIÓN DEL SISTEMA DE CACHÉ

## 📋 Variables de Entorno Requeridas

### Para Redis (Producción Recomendado):

```bash
# Opción 1: URL completa (preferido)
REDIS_URL=redis://:password@host:6379/0

# Opción 2: Componentes individuales
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-password  # Opcional
REDIS_SOCKET_TIMEOUT=5
```

### Para Render.com:

Si tienes un servicio Redis en Render, obtén la URL de conexión y configúrala como:

```bash
REDIS_URL=redis://default:password@redis-host:6379
```

O si Render proporciona componentes separados:

```bash
REDIS_HOST=your-redis-service.onrender.com
REDIS_PORT=6379
REDIS_PASSWORD=your-password
```

## 🔍 Verificación

### Logs de Inicialización:

**Si Redis está configurado:**
```
✅ Redis cache inicializado correctamente
🔗 Conectando a Redis usando REDIS_URL: host:6379/0
```

**Si Redis no está disponible:**
```
⚠️ Redis no disponible, usando MemoryCache
⚠️ Usando MemoryCache - NO recomendado para producción con múltiples workers
```

### Logs de Cache Hit/Miss:

Busca en los logs:
```
✅ [kpis_pagos] Cache HIT para mes 11/2025
❌ [kpis_pagos] Cache MISS para mes 11/2025, calculando...
```

## 📊 Endpoints con Caché

Todos estos endpoints tienen caché de 5 minutos (300 segundos):

- `/api/v1/dashboard/admin`
- `/api/v1/dashboard/kpis-principales`
- `/api/v1/dashboard/cobranzas-mensuales`
- `/api/v1/dashboard/morosidad-por-analista`
- `/api/v1/dashboard/evolucion-general-mensual`
- `/api/v1/dashboard/financiamiento-tendencia-mensual`
- `/api/v1/dashboard/evolucion-morosidad`
- `/api/v1/dashboard/evolucion-pagos`
- `/api/v1/dashboard/opciones-filtros` (10 min)
- `/api/v1/kpis/dashboard`
- `/api/v1/kpis/financiamiento-por-estado`
- `/api/v1/kpis/amortizaciones`
- `/api/v1/kpis/mes-actual`
- `/api/v1/notificaciones/estadisticas/resumen`
- `/api/v1/pagos/kpis`

## 🚀 Próximos Pasos

1. **Configurar Redis en Render.com:**
   - Crear servicio Redis
   - Copiar URL de conexión
   - Agregar como variable de entorno `REDIS_URL`

2. **Verificar funcionamiento:**
   - Revisar logs de inicio
   - Verificar Cache HIT/MISS en logs
   - Monitorear tiempos de respuesta

3. **Optimizar TTLs si es necesario:**
   - Ajustar según frecuencia de cambios de datos
   - Considerar invalidación manual para datos críticos

