# 🔍 GUÍA RÁPIDA DE DEBUGGING - Sistema de Pagos

## ⚡ IDENTIFICACIÓN RÁPIDA DE PROBLEMAS

### 🚨 PROBLEMAS COMUNES Y SOLUCIONES INMEDIATAS

#### 1. **Gráfico no muestra todas las variables**

**Síntomas:**
- El gráfico muestra algunas líneas pero no todas
- Los logs muestran datos pero no aparecen en el gráfico

**Debug Rápido:**
```bash
# 1. Verificar logs del endpoint
grep "financiamiento-tendencia" logs/app.log | tail -20

# 2. Verificar dominio del eje Y
grep "Dominio del eje Y" logs/app.log | tail -5

# 3. Verificar datos recibidos
grep "DEBUG INFO" logs/app.log | tail -10
```

**Solución:**
- Verificar que `yAxisDomain` incluya todos los valores máximos
- Revisar que todas las series tengan `dataKey` correcto
- Verificar que los datos no sean `null` o `undefined`

**Código de verificación:**
```python
# En frontend/src/pages/DashboardMenu.tsx
# El dominio se calcula automáticamente con useMemo
# Si hay problemas, revisar:
console.log('yAxisDomain:', yAxisDomain)
console.log('datosTendencia:', datosTendencia)
```

---

#### 2. **Error SQL: `%(fecha_inicio)s` o parámetros incorrectos**

**Síntomas:**
- Error en logs: `%(fecha_inicio)s` o formato incorrecto
- Endpoint devuelve 500 o error de base de datos

**Debug Rápido:**
```bash
# Buscar errores SQL en logs
grep "ERROR SQL DETECTADO" logs/app.log | tail -10

# Ver query y parámetros
grep "Query:" logs/app.log | tail -5
grep "Parámetros:" logs/app.log | tail -5
```

**Solución:**
- Verificar que se use `bindparams()` y no f-strings en queries SQL
- Asegurar que fechas sean objetos `datetime`, no `date`
- Revisar que los parámetros se pasen correctamente

**Código de verificación:**
```python
# En backend/app/api/v1/endpoints/dashboard.py
# Asegurar conversión de fechas:
if isinstance(fecha_primera, date) and not isinstance(fecha_primera, datetime):
    fecha_primera = datetime.combine(fecha_primera, datetime.min.time())
```

---

#### 3. **Morosidad se muestra como acumulativa en lugar de mensual**

**Síntomas:**
- La línea de morosidad siempre aumenta
- No refleja pagos realizados

**Debug Rápido:**
```bash
# Verificar cálculo de morosidad
grep "morosidad_mensual" logs/app.log | grep "Programado\|Pagado" | tail -10

# Verificar fórmula
grep "MAX(0, Programado - Pagado)" logs/app.log
```

**Solución:**
- Verificar que `morosidad_mensual = max(0, monto_cuotas_programadas - monto_pagado_mes)`
- Asegurar que NO se acumule entre meses
- Verificar que el frontend use `dataKey="morosidad_mensual"`

---

#### 4. **Query lenta (>8 segundos)**

**Síntomas:**
- Endpoint tarda mucho en responder
- Timeout en frontend

**Debug Rápido:**
```bash
# Ver alertas de queries lentas
grep "QUERY LENTA DETECTADA" logs/app.log | tail -10

# Ver tiempos de respuesta
grep "responseTimeMS" logs/app.log | awk '{print $NF}' | sort -n | tail -10
```

**Solución:**
- Revisar índices en base de datos
- Optimizar queries con JOINs innecesarios
- Considerar aumentar cache TTL

---

#### 5. **Datos faltantes o campos incorrectos**

**Síntomas:**
- Gráfico muestra "No hay datos disponibles"
- Algunos campos son `null` o `undefined`

**Debug Rápido:**
```bash
# Ver alertas de datos faltantes
grep "DATOS FALTANTES DETECTADOS" logs/app.log | tail -10

# Verificar checklist de debugging
grep "DEBUG CHECKLIST" logs/app.log | tail -10
```

**Solución:**
- Verificar que el endpoint devuelva todos los campos requeridos
- Revisar validación de datos en `validate_graph_data()`
- Verificar que los datos no sean `None` o vacíos

---

## 📋 CHECKLIST DE DEBUGGING (5 MINUTOS)

### Paso 1: Verificar Logs (1 min)
```bash
# Ver últimos errores
tail -50 logs/app.log | grep -E "ERROR|WARNING|🚨|⚠️"

# Ver endpoint específico
tail -100 logs/app.log | grep "financiamiento-tendencia"
```

### Paso 2: Verificar Datos (1 min)
```bash
# Verificar que el endpoint devuelve datos
curl -H "Authorization: Bearer TOKEN" \
  https://rapicredit.onrender.com/api/v1/dashboard/financiamiento-tendencia-mensual?meses=12 \
  | jq '.meses | length'

# Verificar estructura de datos
curl -H "Authorization: Bearer TOKEN" \
  https://rapicredit.onrender.com/api/v1/dashboard/financiamiento-tendencia-mensual?meses=12 \
  | jq '.meses[0]'
```

### Paso 3: Verificar Frontend (1 min)
```javascript
// En consola del navegador
// Verificar datos recibidos
console.log('datosTendencia:', datosTendencia)
console.log('yAxisDomain:', yAxisDomain)

// Verificar que todas las series tienen datos
datosTendencia?.forEach((d, i) => {
  console.log(`Mes ${i}:`, {
    monto_nuevos: d.monto_nuevos,
    monto_cuotas_programadas: d.monto_cuotas_programadas,
    monto_pagado: d.monto_pagado,
    morosidad_mensual: d.morosidad_mensual
  })
})
```

### Paso 4: Verificar Errores SQL (1 min)
```bash
# Buscar errores SQL recientes
grep "ERROR SQL DETECTADO" logs/app.log | tail -5

# Ver stack trace completo
grep -A 20 "ERROR SQL DETECTADO" logs/app.log | tail -25
```

### Paso 5: Verificar Performance (1 min)
```bash
# Ver queries lentas
grep "QUERY LENTA DETECTADA" logs/app.log | tail -5

# Ver tiempos de respuesta
grep "responseTimeMS" logs/app.log | awk '{if ($NF > 5000) print}' | tail -10
```

---

## 🔧 HERRAMIENTAS DE DEBUGGING DISPONIBLES

### 1. **DebugAlert** (backend/app/core/debug_helpers.py)
```python
from app.core.debug_helpers import DebugAlert

# Log error SQL con contexto completo
DebugAlert.log_sql_error(error, query, params)

# Alerta de query lenta
DebugAlert.log_slow_query(endpoint, duration_ms, threshold_ms=5000)

# Alerta de datos faltantes
DebugAlert.log_missing_data(endpoint, expected_field, data)

# Alerta de error en gráfico
DebugAlert.log_graph_error(endpoint, error, data_sample)
```

### 2. **Decoradores de Debugging**
```python
from app.core.debug_helpers import debug_timing, debug_sql_errors

@debug_timing(threshold_ms=8000)
def mi_endpoint():
    # Alertará si tarda más de 8 segundos
    pass

@debug_sql_errors
def mi_query():
    # Capturará y loggeará errores SQL automáticamente
    pass
```

### 3. **Validación de Datos**
```python
from app.core.debug_helpers import validate_graph_data

is_valid, error_msg = validate_graph_data(
    data=meses_data,
    required_fields=['mes', 'monto_nuevos', 'monto_cuotas_programadas']
)

if not is_valid:
    logger.error(f"Datos inválidos: {error_msg}")
```

### 4. **Log de Información de Gráficos**
```python
from app.core.debug_helpers import log_graph_debug_info

log_graph_debug_info(
    endpoint="/financiamiento-tendencia-mensual",
    data=meses_data,
    y_axis_domain=[0, 100000]
)
```

### 5. **Checklist Automático**
```python
from app.core.debug_helpers import run_debug_checklist

results = run_debug_checklist(
    endpoint="/financiamiento-tendencia-mensual",
    data=meses_data,
    required_fields=['mes', 'monto_nuevos', 'monto_cuotas_programadas']
)

# results contiene:
# {
#   "endpoint": "...",
#   "timestamp": "...",
#   "checks": {
#     "data_not_empty": True,
#     "required_fields": True,
#     "valid_numeric_values": True
#   }
# }
```

---

## 🚨 ALERTAS AUTOMÁTICAS

El sistema ahora genera alertas automáticas para:

1. **Errores SQL**: Con query, parámetros y stack trace completo
2. **Queries Lentas**: Cuando tardan más del umbral configurado
3. **Datos Faltantes**: Cuando faltan campos requeridos
4. **Errores en Gráficos**: Con contexto completo del error
5. **Valores Inválidos**: Cuando los valores numéricos no son válidos

---

## 📞 CONTACTO RÁPIDO

Si después de seguir esta guía el problema persiste:

1. **Recopilar información:**
   ```bash
   # Últimos 100 logs con errores
   grep -E "ERROR|WARNING|🚨|⚠️" logs/app.log | tail -100 > debug_logs.txt
   
   # Stack traces completos
   grep -A 30 "ERROR SQL DETECTADO" logs/app.log | tail -50 > sql_errors.txt
   ```

2. **Verificar estado del sistema:**
   ```bash
   # Health check
   curl https://rapicredit.onrender.com/api/v1/health
   
   # Estado de monitoreo
   curl -H "Authorization: Bearer TOKEN" \
     https://rapicredit.onrender.com/api/v1/configuracion/monitoreo/estado
   ```

3. **Documentar el problema:**
   - ¿Qué endpoint falla?
   - ¿Qué error específico aparece?
   - ¿Cuándo empezó el problema?
   - ¿Qué cambios se hicieron recientemente?

---

## ✅ PREVENCIÓN DE PROBLEMAS

### Mejores Prácticas:

1. **Siempre usar `bindparams()` en queries SQL**
2. **Validar tipos de datos antes de pasarlos a queries**
3. **Usar decoradores de debugging en endpoints críticos**
4. **Revisar logs regularmente para detectar problemas temprano**
5. **Probar cambios en desarrollo antes de producción**

### Configuración Recomendada:

```python
# En settings.py
LOG_LEVEL = "INFO"  # Para producción
# LOG_LEVEL = "DEBUG"  # Para debugging

# Umbrales de alerta
SLOW_QUERY_THRESHOLD_MS = 5000  # 5 segundos
SLOW_ENDPOINT_THRESHOLD_MS = 8000  # 8 segundos
```

---

**Última actualización:** 2025-11-06  
**Versión:** 1.0

