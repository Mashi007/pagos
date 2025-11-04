# Sistema de Monitoreo de Performance

Este documento describe el sistema de monitoreo de performance implementado para identificar y analizar endpoints lentos.

## Componentes

### 1. Performance Monitor (`app/core/performance_monitor.py`)

Módulo que almacena métricas de performance en memoria:
- Almacena métricas por endpoint (método + ruta)
- Calcula estadísticas: promedio, mínimo, máximo, tasa de errores
- Mantiene historial de últimas peticiones
- Limpieza automática de métricas antiguas

### 2. Performance Logging Middleware (`app/main.py`)

Middleware que registra automáticamente cada petición:
- Tiempo de respuesta (ms)
- Tamaño de respuesta (bytes)
- Código de estado HTTP
- Logs estructurados con emojis según el tiempo de respuesta:
  - 🐌 > 5000ms (ERROR)
  - ⚠️ > 2000ms (WARNING)
  - ⏱️ > 1000ms (INFO)
  - ✅ ≤ 1000ms (DEBUG)

### 3. Endpoints de Monitoreo

#### GET `/api/v1/performance/summary`

Resumen general de todas las métricas:

```json
{
  "status": "success",
  "summary": {
    "total_endpoints": 25,
    "total_requests": 1500,
    "avg_response_time_ms": 245.5,
    "total_errors": 12,
    "error_rate": 0.8,
    "monitoring_since": "2025-01-15T10:30:00"
  },
  "timestamp": 1705316400.0
}
```

#### GET `/api/v1/performance/slow?threshold_ms=1000&limit=20`

Lista de endpoints lentos ordenados por tiempo promedio:

**Parámetros:**
- `threshold_ms` (opcional, default: 1000): Umbral mínimo en ms para considerar lento
- `limit` (opcional, default: 20): Número máximo de resultados

**Ejemplo de respuesta:**
```json
{
  "status": "success",
  "threshold_ms": 1000,
  "count": 5,
  "endpoints": [
    {
      "endpoint": "GET /api/v1/cobranzas/clientes-atrasados",
      "method": "GET",
      "path": "/api/v1/cobranzas/clientes-atrasados",
      "count": 45,
      "avg_time_ms": 8500.25,
      "min_time_ms": 3200.0,
      "max_time_ms": 12500.0,
      "total_time_ms": 382511.25,
      "error_rate": 2.22,
      "last_request": "2025-01-15T15:30:00"
    }
  ],
  "timestamp": 1705316400.0
}
```

#### GET `/api/v1/performance/endpoint/{method}/{path}`

Estadísticas detalladas de un endpoint específico:

**Ejemplo:**
```
GET /api/v1/performance/endpoint/GET/api/v1/pagos/kpis
```

**Ejemplo de respuesta:**
```json
{
  "status": "success",
  "stats": {
    "endpoint": "GET /api/v1/pagos/kpis",
    "method": "GET",
    "path": "/api/v1/pagos/kpis",
    "count": 120,
    "avg_time_ms": 450.5,
    "min_time_ms": 120.0,
    "max_time_ms": 850.0,
    "total_time_ms": 54060.0,
    "error_count": 0,
    "error_rate": 0.0,
    "avg_response_bytes": 2450.5,
    "percentile_50_bytes": 2400,
    "percentile_95_bytes": 2800,
    "last_request": "2025-01-15T15:30:00"
  },
  "timestamp": 1705316400.0
}
```

#### GET `/api/v1/performance/recent?limit=50`

Últimas peticiones registradas:

**Parámetros:**
- `limit` (opcional, default: 50, max: 200): Número de peticiones a retornar

**Ejemplo de respuesta:**
```json
{
  "status": "success",
  "count": 50,
  "requests": [
    {
      "timestamp": "2025-01-15T15:30:00",
      "method": "GET",
      "path": "/api/v1/pagos/kpis",
      "response_time_ms": 450.5,
      "status_code": 200,
      "response_bytes": 2450
    }
  ],
  "timestamp": 1705316400.0
}
```

### 4. Script de Análisis de Logs

Script para analizar logs históricos y generar reportes:

**Ubicación:** `backend/scripts/analizar_logs_performance.py`

**Uso:**
```bash
# Análisis básico (umbral 1000ms, top 20)
python scripts/analizar_logs_performance.py logs/app.log

# Con umbral personalizado
python scripts/analizar_logs_performance.py logs/app.log --threshold 2000

# Con límite de resultados
python scripts/analizar_logs_performance.py logs/app.log --threshold 1000 --limit 10
```

**Ejemplo de salida:**
```
📊 REPORTE DE ANÁLISIS DE PERFORMANCE
================================================================================

📈 Estadísticas Generales:
   - Líneas totales procesadas: 5,234
   - Líneas parseadas: 4,891
   - Endpoints únicos: 45
   - Umbral de tiempo: 1000ms

🐌 Endpoints Lentos (Top 10):
--------------------------------------------------------------------------------
Endpoint                                           Count    Avg(ms)    Max(ms)    Errors
--------------------------------------------------------------------------------
GET /api/v1/cobranzas/clientes-atrasados          45       8,500.25   12,500.00   ⚠️ 2.2%
GET /api/v1/cobranzas/notificaciones/atrasos      32       5,200.10   8,300.00    ✅ 0.0%
...
```

## Configuración

### Retención de Métricas

Por defecto, el monitor mantiene:
- **Métricas en memoria:** Hasta 1000 endpoints únicos
- **Retención:** 24 horas
- **Historial de peticiones:** Últimas 500 peticiones

Para modificar estos valores, edita `app/core/performance_monitor.py`:

```python
performance_monitor = PerformanceMonitor(
    max_entries=1000,      # Máximo de endpoints únicos
    retention_hours=24    # Horas de retención
)
```

## Uso Recomendado

### Monitoreo en Tiempo Real

1. **Consultar resumen general:**
   ```bash
   curl http://localhost:8000/api/v1/performance/summary
   ```

2. **Identificar endpoints lentos:**
   ```bash
   curl "http://localhost:8000/api/v1/performance/slow?threshold_ms=2000&limit=10"
   ```

3. **Analizar un endpoint específico:**
   ```bash
   curl "http://localhost:8000/api/v1/performance/endpoint/GET/api/v1/pagos/kpis"
   ```

### Análisis de Logs Históricos

Para analizar logs acumulados:

```bash
# Si tienes logs en formato estándar
python scripts/analizar_logs_performance.py logs/app.log --threshold 2000

# Redirigir salida a un archivo
python scripts/analizar_logs_performance.py logs/app.log > reporte_performance.txt
```

## Integración con Monitoreo

### Alertas Automáticas

El middleware genera logs con diferentes niveles según el tiempo de respuesta:
- Los logs con nivel ERROR (>5000ms) pueden ser capturados por sistemas de monitoreo
- Los logs con nivel WARNING (>2000ms) indican degradación de performance

### Ejemplo de integración con Prometheus/Grafana

Los endpoints de performance pueden ser consultados por sistemas de monitoreo externos para:
- Generar dashboards
- Configurar alertas
- Analizar tendencias

## Limitaciones

1. **Métricas en memoria:** Las métricas se pierden al reiniciar el servidor
2. **No persistente:** No se guardan en base de datos
3. **Limitado por memoria:** Para sistemas con muchos endpoints, considerar aumentar `max_entries`

## Próximas Mejoras

- [ ] Persistencia de métricas en base de datos
- [ ] Exportación de métricas a sistemas externos (Prometheus, etc.)
- [ ] Alertas automáticas por email/webhook
- [ ] Dashboard web integrado
- [ ] Análisis de tendencias históricas

