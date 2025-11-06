# 🔍 Sistema de Monitoreo y Alertas Implementado

## ✅ Resumen

He implementado un **sistema completo de monitoreo, logging y alertas** para detectar errores y problemas de rendimiento en tiempo real.

---

## 🎯 Componentes Implementados

### 1. **Query Monitor** (`backend/app/utils/query_monitor.py`)

Sistema de monitoreo específico para queries SQL que:
- ✅ Registra tiempo de ejecución de cada query
- ✅ Detecta queries lentas automáticamente
- ✅ Genera alertas por severidad (CRITICAL, HIGH, MEDIUM)
- ✅ Mantiene historial de queries y errores
- ✅ Calcula métricas agregadas (promedio, min, max, tasa de error)

**Umbrales de alerta:**
- 🟢 **Normal**: < 1 segundo
- 🟡 **Lento**: ≥ 1 segundo (alerta MEDIUM)
- 🟠 **Crítico**: ≥ 5 segundos (alerta HIGH)
- 🔴 **Muy crítico**: ≥ 10 segundos (alerta CRITICAL)

---

### 2. **Endpoints de Monitoreo** (`backend/app/api/v1/endpoints/monitoring.py`)

Nuevos endpoints para debugging y análisis:

#### `/api/v1/monitoring/queries/slow`
Obtiene queries lentas ordenadas por tiempo promedio
```bash
GET /api/v1/monitoring/queries/slow?threshold_ms=1000&limit=20
```

#### `/api/v1/monitoring/queries/stats/{query_name}`
Estadísticas detalladas de una query específica
```bash
GET /api/v1/monitoring/queries/stats/obtener_kpis_principales
```

#### `/api/v1/monitoring/queries/summary`
Resumen general de todas las queries
```bash
GET /api/v1/monitoring/queries/summary
```

#### `/api/v1/monitoring/alerts/recent`
Alertas recientes de queries
```bash
GET /api/v1/monitoring/alerts/recent?limit=50&severity=CRITICAL
```

#### `/api/v1/monitoring/dashboard/performance`
Métricas combinadas de endpoints y queries del dashboard
```bash
GET /api/v1/monitoring/dashboard/performance
```

---

### 3. **Logging Mejorado en Endpoints Optimizados**

Se agregó logging estructurado y alertas automáticas en:

#### `obtener_kpis_principales`
- ✅ Registra tiempo de query
- ✅ Alerta si > 5 segundos (CRITICAL)
- ✅ Alerta si > 2 segundos (WARNING)

#### `obtener_financiamiento_tendencia_mensual`
- ✅ Registra tiempo de cada query individual (nuevos, cuotas, pagos)
- ✅ Alerta si alguna query > 5 segundos (CRITICAL)
- ✅ Alerta si alguna query > 2 segundos (WARNING)

#### `obtener_resumen_prestamos_cliente`
- ✅ Registra tiempo de query agregada
- ✅ Alerta si > 2 segundos (WARNING)

---

## 📊 Ejemplos de Logs

### Log Normal (sin alertas)
```
📊 [kpis-principales] Completado en 450ms (query: 420ms)
📊 [financiamiento-tendencia] Query completada en 320ms, 12 meses
```

### Alerta de Query Lenta
```
⚠️ [ALERTA] KPIs principales lento: 2300ms - Considerar optimización
```

### Alerta Crítica
```
🚨 [ALERTA] KPIs principales muy lento: 6200ms - Revisar índices y optimizaciones
🚨 [ALERTA CRÍTICA] Financiamiento tendencia muy lento: 12500ms - URGENTE: Revisar índices
```

### Alerta de Query Individual
```
⚠️ [ALERTA] Query nuevos financiamientos lenta: 2800ms
🚨 [ALERTA CRÍTICA] Query cuotas programadas muy lenta: 7500ms
```

---

## 🔍 Cómo Usar el Sistema

### 1. Ver Queries Lentas

```bash
# Ver todas las queries lentas (>1 segundo)
curl -X GET "http://localhost:8000/api/v1/monitoring/queries/slow?threshold_ms=1000" \
  -H "Authorization: Bearer tu_token"
```

### 2. Ver Estadísticas de una Query Específica

```bash
# Ver estadísticas de KPIs principales
curl -X GET "http://localhost:8000/api/v1/monitoring/queries/stats/obtener_kpis_principales" \
  -H "Authorization: Bearer tu_token"
```

### 3. Ver Alertas Recientes

```bash
# Ver alertas críticas recientes
curl -X GET "http://localhost:8000/api/v1/monitoring/alerts/recent?severity=CRITICAL&limit=20" \
  -H "Authorization: Bearer tu_token"
```

### 4. Ver Resumen de Performance del Dashboard

```bash
# Ver métricas completas del dashboard
curl -X GET "http://localhost:8000/api/v1/monitoring/dashboard/performance" \
  -H "Authorization: Bearer tu_token"
```

---

## 📈 Métricas Disponibles

### Por Query Individual:
- `count`: Número de ejecuciones
- `avg_time_ms`: Tiempo promedio en ms
- `min_time_ms`: Tiempo mínimo
- `max_time_ms`: Tiempo máximo
- `slow_query_count`: Número de queries lentas (>1s)
- `critical_query_count`: Número de queries críticas (>5s)
- `error_count`: Número de errores
- `error_rate`: Porcentaje de errores
- `last_execution`: Última ejecución

### Resumen General:
- `total_queries`: Total de queries monitoreadas
- `total_executions`: Total de ejecuciones
- `avg_execution_time_ms`: Tiempo promedio general
- `total_errors`: Total de errores
- `error_rate`: Tasa de error general
- `slow_query_rate`: Tasa de queries lentas

---

## 🚨 Alertas Automáticas

El sistema genera alertas automáticamente cuando:

1. **Query lenta** (≥ 1 segundo):
   - Severidad: MEDIUM
   - Log: `⏱️ [QUERY LENTA]`
   - Acción: Revisar optimizaciones

2. **Query crítica** (≥ 5 segundos):
   - Severidad: HIGH
   - Log: `⚠️ [QUERY LENTA]`
   - Acción: Revisar índices y optimizaciones urgentes

3. **Query muy crítica** (≥ 10 segundos):
   - Severidad: CRITICAL
   - Log: `🚨 [QUERY CRÍTICA]`
   - Acción: URGENTE - Revisar índices y optimizaciones

4. **Error en query**:
   - Severidad: HIGH
   - Log: `❌ [ERROR QUERY]`
   - Acción: Revisar error y corregir

---

## 🔧 Configuración

Los umbrales están definidos en `backend/app/utils/query_monitor.py`:

```python
SLOW_QUERY_THRESHOLD_MS = 1000      # 1 segundo
CRITICAL_QUERY_THRESHOLD_MS = 5000  # 5 segundos
VERY_SLOW_QUERY_THRESHOLD_MS = 10000 # 10 segundos
```

Puedes modificar estos valores según tus necesidades.

---

## 📝 Queries Monitoreadas Actualmente

1. ✅ `obtener_kpis_principales` - KPIs del dashboard
2. ✅ `financiamiento_tendencia_nuevos` - Nuevos financiamientos por mes
3. ✅ `financiamiento_tendencia_cuotas` - Cuotas programadas por mes
4. ✅ `financiamiento_tendencia_pagos` - Pagos por mes
5. ✅ `obtener_resumen_prestamos_cliente_cuotas` - Cuotas agregadas por préstamo

---

## 🎯 Próximos Pasos

1. **Monitorear logs** después de ejecutar índices
2. **Verificar alertas** en `/api/v1/monitoring/alerts/recent`
3. **Comparar métricas** antes/después de optimizaciones
4. **Ajustar umbrales** si es necesario

---

## ✅ Beneficios

- 🔍 **Detección temprana** de problemas de rendimiento
- 📊 **Métricas en tiempo real** de queries
- 🚨 **Alertas automáticas** cuando algo va mal
- 🐛 **Debugging facilitado** con estadísticas detalladas
- 📈 **Análisis de tendencias** de rendimiento

---

## 🎉 Resultado

Ahora tienes un **sistema completo de monitoreo** que:
- ✅ Detecta queries lentas automáticamente
- ✅ Genera alertas por severidad
- ✅ Proporciona métricas detalladas
- ✅ Facilita debugging y optimización
- ✅ Ayuda a identificar problemas antes de que afecten a usuarios

