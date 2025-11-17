# 📊 Guía de Monitoreo y Optimización de Performance

Esta guía explica cómo monitorear y mejorar el rendimiento de la aplicación después del despliegue.

## 🎯 Objetivos

1. **Monitorear tiempos de respuesta** en tiempo real
2. **Verificar el cache** y su efectividad
3. **Identificar cuellos de botella** en endpoints específicos
4. **Verificar índices** en la base de datos
5. **Analizar logs** para encontrar patrones

---

## 1. Monitoreo en Tiempo Real

### Usar el Script de Monitoreo

```bash
# Monitoreo básico (actualiza cada 30 segundos)
python backend/scripts/monitorear_performance_tiempo_real.py

# Monitoreo con intervalo personalizado
python backend/scripts/monitorear_performance_tiempo_real.py --intervalo 60

# Monitoreo con umbral personalizado para endpoints lentos
python backend/scripts/monitorear_performance_tiempo_real.py --threshold 2000

# Monitoreo de producción
python backend/scripts/monitorear_performance_tiempo_real.py \
    --url https://pagos-f2qf.onrender.com/api/v1 \
    --intervalo 30
```

### Usar los Endpoints de la API

#### Obtener Resumen General

```bash
curl https://pagos-f2qf.onrender.com/api/v1/performance/summary
```

**Respuesta:**
```json
{
  "status": "success",
  "summary": {
    "total_endpoints": 25,
    "total_requests": 1500,
    "avg_response_time_ms": 245.5,
    "total_errors": 12,
    "error_rate": 0.8
  }
}
```

#### Obtener Endpoints Lentos

```bash
# Endpoints con tiempo promedio > 1000ms
curl https://pagos-f2qf.onrender.com/api/v1/performance/slow?threshold_ms=1000

# Endpoints con tiempo promedio > 2000ms
curl https://pagos-f2qf.onrender.com/api/v1/performance/slow?threshold_ms=2000&limit=10
```

#### Obtener Estadísticas de un Endpoint Específico

```bash
curl https://pagos-f2qf.onrender.com/api/v1/performance/endpoint/GET/api/v1/dashboard/admin
```

#### Obtener Peticiones Recientes

```bash
curl https://pagos-f2qf.onrender.com/api/v1/performance/recent?limit=20
```

---

## 2. Verificar el Cache

### Verificar Cache en Logs

Busca en los logs del servidor mensajes de cache:

```bash
# En Render Dashboard → Logs
grep "Cache HIT\|Cache MISS" logs.txt
```

**Ejemplos de logs:**
- `✅ [kpis_pagos] Cache HIT para mes 11/2025` - Cache funcionando
- `❌ [kpis_pagos] Cache MISS para mes 11/2025, calculando...` - Cache no activo

### Verificar Tiempos de Respuesta

**Primera petición (cache miss):** Tiempo más alto (ej: 3000ms)
**Peticiones subsecuentes (cache hit):** Tiempo mucho menor (ej: 50ms)

Si los tiempos no mejoran en peticiones subsecuentes, el cache puede no estar funcionando.

### Endpoints con Cache

Los siguientes endpoints tienen cache de 5 minutos (300 segundos):

- `/api/v1/dashboard/admin`
- `/api/v1/dashboard/kpis-principales`
- `/api/v1/dashboard/evolucion-morosidad`
- `/api/v1/dashboard/evolucion-pagos`
- `/api/v1/dashboard/cobranzas-mensuales`
- `/api/v1/pagos/kpis`

---

## 3. Verificar Índices en la Base de Datos

### Usar el Script de Verificación

```bash
python backend/scripts/verificar_indices_bd.py
```

Este script:
- ✅ Lista todos los índices existentes
- ❌ Identifica índices faltantes recomendados
- 📊 Muestra estadísticas de cada tabla (filas, tamaño)
- ⚠️ Prioriza índices de prioridad ALTA

### Índices Críticos para Performance

#### Índices Funcionales (Más Importantes)

```sql
-- Para queries con GROUP BY por año/mes en cuotas
CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento_funcional
ON cuotas (EXTRACT(YEAR FROM fecha_vencimiento), EXTRACT(MONTH FROM fecha_vencimiento));

-- Para queries con GROUP BY por año/mes en pagos_staging
CREATE INDEX IF NOT EXISTS idx_pagos_staging_fecha_pago_funcional
ON pagos_staging (EXTRACT(YEAR FROM fecha_pago::timestamp), EXTRACT(MONTH FROM fecha_pago::timestamp))
WHERE fecha_pago IS NOT NULL AND fecha_pago != '';
```

#### Índices Regulares (También Importantes)

```sql
-- Prestamos
CREATE INDEX IF NOT EXISTS idx_prestamos_estado ON prestamos(estado);
CREATE INDEX IF NOT EXISTS idx_prestamos_fecha_registro ON prestamos(fecha_registro);

-- Cuotas
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_id ON cuotas(prestamo_id);
CREATE INDEX IF NOT EXISTS idx_cuotas_estado ON cuotas(estado);
CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento ON cuotas(fecha_vencimiento);

-- Pagos Staging
CREATE INDEX IF NOT EXISTS idx_pagos_staging_fecha_pago ON pagos_staging(fecha_pago);

-- Clientes
CREATE INDEX IF NOT EXISTS idx_clientes_cedula ON clientes(cedula);
```

### Ejecutar Índices en la Base de Datos

1. **Conectarse a la base de datos** (DBeaver, pgAdmin, etc.)
2. **Ejecutar los scripts SQL** del script de verificación
3. **Verificar que se crearon** con:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'cuotas'
ORDER BY indexname;
```

---

## 4. Analizar Logs de Performance

### Usar el Script de Análisis

```bash
# Analizar logs del servidor
python backend/scripts/analizar_logs_performance.py logs.txt

# Con umbral personalizado
python backend/scripts/analizar_logs_performance.py logs.txt --threshold 2000

# Con límite de resultados
python backend/scripts/analizar_logs_performance.py logs.txt --limit 10
```

### Buscar Patrones en Logs

#### Endpoints Más Lentos

```bash
# Buscar requests > 5000ms (🐌)
grep "🐌" logs.txt | grep "responseTimeMS" | sort -k5 -n -r | head -20

# Buscar requests > 2000ms (⚠️)
grep "⚠️" logs.txt | grep "responseTimeMS" | sort -k5 -n -r | head -20
```

#### Errores de Performance

```bash
# Buscar errores relacionados con performance
grep -E "ERROR.*performance|ERROR.*slow|ERROR.*timeout" logs.txt
```

#### Cache Hits/Misses

```bash
# Ver efectividad del cache
grep "Cache HIT\|Cache MISS" logs.txt | tail -50
```

---

## 5. Identificar Cuellos de Botella

### Métricas a Observar

1. **Tiempo de respuesta promedio:**
   - ✅ Bueno: < 500ms
   - ⚠️ Aceptable: 500-2000ms
   - ❌ Lento: > 2000ms

2. **Tasa de errores:**
   - ✅ Bueno: < 1%
   - ⚠️ Aceptable: 1-5%
   - ❌ Crítico: > 5%

3. **Endpoints más solicitados:**
   - Verificar si hay carga concentrada en pocos endpoints

### Proceso de Optimización

1. **Identificar endpoints lentos** usando `/api/v1/performance/slow`
2. **Analizar el código** del endpoint específico
3. **Verificar queries** y optimizarlas:
   - Reducir número de queries
   - Usar JOINs eficientes
   - Aprovechar índices
4. **Agregar cache** si es apropiado
5. **Verificar índices** en tablas relacionadas
6. **Probar mejoras** y medir impacto

---

## 6. Checklist de Optimización

### ✅ Verificaciones Post-Despliegue

- [ ] Ejecutar script de verificación de índices
- [ ] Verificar que índices críticos están presentes
- [ ] Monitorear tiempos de respuesta en las primeras horas
- [ ] Verificar que el cache está funcionando (logs)
- [ ] Identificar endpoints que aún son lentos
- [ ] Analizar logs para encontrar patrones

### ✅ Optimizaciones Recomendadas

- [ ] Crear índices funcionales para GROUP BY por año/mes
- [ ] Verificar índices en columnas usadas en JOINs
- [ ] Asegurar que queries usan índices (EXPLAIN ANALYZE)
- [ ] Agregar cache a endpoints que no lo tienen
- [ ] Optimizar queries que hacen múltiples consultas
- [ ] Considerar paginación para endpoints que retornan muchos datos

---

## 7. Ejemplos de Uso

### Monitoreo Continuo

```bash
# Terminal 1: Monitoreo en tiempo real
python backend/scripts/monitorear_performance_tiempo_real.py \
    --url https://pagos-f2qf.onrender.com/api/v1 \
    --intervalo 60

# Terminal 2: Verificar índices
python backend/scripts/verificar_indices_bd.py

# Terminal 3: Analizar logs
python backend/scripts/analizar_logs_performance.py logs.txt
```

### Verificar Mejoras

```bash
# Antes de optimización
curl https://pagos-f2qf.onrender.com/api/v1/performance/summary > metrics_before.json

# Después de optimización
curl https://pagos-f2qf.onrender.com/api/v1/performance/summary > metrics_after.json

# Comparar
diff metrics_before.json metrics_after.json
```

---

## 8. Contacto y Soporte

Si encuentras problemas de performance que no se resuelven con estas herramientas:

1. Revisar logs detallados del servidor
2. Verificar métricas de la base de datos
3. Analizar queries específicas con `EXPLAIN ANALYZE`
4. Considerar escalado horizontal si es necesario

---

**Última actualización:** 2025-11-04

