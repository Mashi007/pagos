# 🔍 ANÁLISIS: PROBLEMA DE RENDIMIENTO EN DASHBOARD

**Fecha:** 2025-11-06  
**Problema:** Tiempos de respuesta muy altos (1-5+ segundos) en endpoints del dashboard

---

## 📊 SÍNTOMAS OBSERVADOS

### Logs de Producción (2025-11-06T02:00:11Z)

**Múltiples peticiones simultáneas del dashboard:**
- `/api/v1/dashboard/kpis-principales` → 822ms
- `/api/v1/dashboard/opciones-filtros` → 346ms
- `/api/v1/dashboard/prestamos-por-concesionario` → 759ms
- `/api/v1/dashboard/financiamiento-tendencia-mensual` → 1225ms
- `/api/v1/dashboard/pagos-conciliados` → 1445ms
- `/api/v1/dashboard/evolucion-morosidad` → 1668ms
- `/api/v1/dashboard/prestamos-por-modelo` → 1950ms
- `/api/v1/dashboard/cobranzas-semanales` → 1822ms
- `/api/v1/dashboard/admin` → 2948ms
- `/api/v1/dashboard/financiamiento-por-rangos` → 2941ms
- `/api/v1/dashboard/cobranzas-mensuales` → 3214ms
- `/api/v1/dashboard/resumen-financiamiento-pagado` → 3146ms
- `/api/v1/dashboard/morosidad-por-analista` → 3225ms
- `/api/v1/dashboard/composicion-morosidad` → 3590ms
- `/api/v1/dashboard/evolucion-pagos` → 4598ms
- `/api/v1/dashboard/financiamiento-por-rangos` → 5097ms
- `/api/v1/dashboard/admin` → 5161ms

**Total: 17 endpoints ejecutándose simultáneamente en ~2 segundos**

---

## 🔴 PROBLEMA PRINCIPAL

### 1. **Cache No Funcional en Producción**

**Causa Raíz:**
- El sistema usa `MemoryCache` (cache en memoria) porque Redis no está disponible
- **MemoryCache NO funciona con múltiples workers** en producción:
  - Cada worker de Gunicorn tiene su propia memoria
  - No hay sincronización entre workers
  - El cache se duplica innecesariamente
  - Cada worker calcula los mismos datos independientemente

**Evidencia:**
```python
# backend/app/core/cache.py
cache_backend: CacheBackend = MemoryCache()  # Fallback cuando Redis falla
```

**Logs esperados (si Redis funcionara):**
```
✅ Redis cache inicializado correctamente
```

**Logs actuales (producción):**
```
⚠️ Usando MemoryCache - NO recomendado para producción con múltiples workers
```

### 2. **Múltiples Peticiones Simultáneas**

**Problema:**
- El frontend carga el dashboard y hace **17 peticiones API simultáneas**
- Todas son cache MISS (primera carga o cache expirado)
- Todas ejecutan queries complejas a la BD al mismo tiempo
- Esto satura la base de datos

**Impacto:**
- 17 queries complejas ejecutándose simultáneamente
- Sin cache compartido, cada worker calcula todo desde cero
- Tiempo de respuesta total: **5+ segundos**

### 3. **Redis No Instalado en Producción**

**Evidencia:**
```python
# backend/requirements/prod.txt
# redis==5.0.1  # COMENTADO - No instalado
```

**Consecuencia:**
- El sistema siempre usa MemoryCache como fallback
- Cache no funciona entre workers
- Cada petición calcula todo desde cero

---

## ✅ SOLUCIONES PROPUESTAS

### **SOLUCIÓN 1: Configurar Redis (CRÍTICO - PRIORIDAD ALTA)**

**Impacto:** 80-95% reducción de tiempo de respuesta  
**Complejidad:** Baja  
**Tiempo:** 30 minutos

#### Pasos:

1. **Instalar Redis en Render.com:**
   - Crear servicio Redis en Render
   - Obtener URL de conexión

2. **Actualizar requirements/prod.txt:**
   ```python
   # Descomentar Redis
   redis==5.0.1
   ```

3. **Configurar variables de entorno en Render:**
   ```bash
   REDIS_URL=redis://default:password@redis-host:6379
   # O componentes individuales:
   REDIS_HOST=your-redis-service.onrender.com
   REDIS_PORT=6379
   REDIS_PASSWORD=your-password
   REDIS_DB=0
   REDIS_SOCKET_TIMEOUT=5
   ```

4. **Verificar logs después del deploy:**
   ```
   ✅ Redis cache inicializado correctamente
   🔗 Conectando a Redis usando REDIS_URL: ...
   ```

**Resultado Esperado:**
- Primera carga: 5 segundos (calcula y cachea)
- Cargas siguientes (5 min): <100ms (cache HIT)
- **Mejora: 95% menos tiempo de respuesta**

---

### **SOLUCIÓN 2: Optimizar Carga del Frontend (MEDIO PLAZO)**

**Impacto:** 50-70% reducción de carga inicial  
**Complejidad:** Media  
**Tiempo:** 2-3 horas

#### Opción A: Carga Paralela con Límite

Limitar peticiones simultáneas a 3-5 en lugar de 17:

```typescript
// frontend/src/components/Dashboard.tsx
// Cargar en batches de 5 peticiones
const loadDashboardData = async () => {
  const batch1 = await Promise.all([
    fetchKpis(),
    fetchOpcionesFiltros(),
    fetchPrestamosConcesionario(),
    fetchFinanciamientoTendencia(),
    fetchPagosConciliados(),
  ]);
  
  // Esperar 200ms antes del siguiente batch
  await new Promise(resolve => setTimeout(resolve, 200));
  
  const batch2 = await Promise.all([
    fetchEvolucionMorosidad(),
    // ... más peticiones
  ]);
  
  // ... más batches
};
```

#### Opción B: Carga Secuencial con Prioridad

Cargar primero los KPIs más importantes, luego el resto:

```typescript
// 1. Cargar KPIs principales primero (críticos)
const kpis = await fetchKpis();

// 2. Cargar opciones de filtros (rápido)
const filtros = await fetchOpcionesFiltros();

// 3. Cargar gráficos en paralelo (menos críticos)
const [graficos1, graficos2, graficos3] = await Promise.all([
  fetchEvolucionMorosidad(),
  fetchEvolucionPagos(),
  fetchPrestamosModelo(),
]);
```

**Resultado Esperado:**
- KPIs principales visibles en <1 segundo
- Resto del dashboard carga progresivamente
- Menos saturación de BD

---

### **SOLUCIÓN 3: Aumentar TTL del Cache (RÁPIDO)**

**Impacto:** 30-50% reducción de regeneración de cache  
**Complejidad:** Muy Baja  
**Tiempo:** 5 minutos

**Cambio:**
```python
# backend/app/api/v1/endpoints/dashboard.py

# ANTES: 5 minutos (300 segundos)
@cache_result(ttl=300, key_prefix="dashboard")

# DESPUÉS: 10 minutos (600 segundos) para datos menos críticos
@cache_result(ttl=600, key_prefix="dashboard")

# Para opciones-filtros (cambian muy poco): 30 minutos
@cache_result(ttl=1800, key_prefix="dashboard")
```

**Endpoints a ajustar:**
- `opciones-filtros`: 1800s (30 min) - Cambian muy poco
- `kpis-principales`: 600s (10 min) - Balance entre frescura y rendimiento
- `evolucion-morosidad`: 600s (10 min) - Datos históricos
- `prestamos-por-concesionario`: 600s (10 min)

**Resultado Esperado:**
- Cache dura más tiempo
- Menos regeneraciones innecesarias
- Menos carga en BD

---

### **SOLUCIÓN 4: Query Batching (LARGO PLAZO)**

**Impacto:** 60-80% reducción de queries  
**Complejidad:** Alta  
**Tiempo:** 8-12 horas

**Idea:**
Crear un endpoint único que devuelva todos los datos del dashboard en una sola petición:

```python
@router.get("/dashboard/completo")
@cache_result(ttl=300, key_prefix="dashboard")
def obtener_dashboard_completo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve todos los datos del dashboard en una sola petición
    Optimizado para reducir queries y aprovechar cache
    """
    # Ejecutar queries en paralelo dentro del servidor
    # Retornar todo en un solo JSON
    return {
        "kpis": calcular_kpis(),
        "filtros": obtener_opciones_filtros(),
        "prestamos_concesionario": calcular_prestamos_concesionario(),
        # ... resto de datos
    }
```

**Resultado Esperado:**
- 1 petición en lugar de 17
- Cache compartido entre todos los datos
- Menos overhead de red

---

## 📋 PLAN DE ACCIÓN RECOMENDADO

### **FASE 1: INMEDIATO (Hoy)**
1. ✅ **Configurar Redis en Render** (30 min)
   - Crear servicio Redis
   - Configurar variables de entorno
   - Descomentar Redis en requirements/prod.txt
   - Deploy y verificar logs

2. ✅ **Aumentar TTL del cache** (5 min)
   - Ajustar TTLs según criticidad
   - Deploy

**Resultado Esperado:** 80-95% mejora en tiempo de respuesta

---

### **FASE 2: CORTO PLAZO (Esta Semana)**
3. ✅ **Optimizar carga del frontend** (2-3 horas)
   - Implementar carga por batches
   - Priorizar KPIs críticos
   - Deploy frontend

**Resultado Esperado:** 50-70% reducción de carga inicial

---

### **FASE 3: MEDIO PLAZO (Próximas 2 Semanas)**
4. ⏳ **Query Batching** (8-12 horas)
   - Crear endpoint consolidado
   - Optimizar queries
   - Actualizar frontend

**Resultado Esperado:** 60-80% reducción de queries totales

---

## 📊 MÉTRICAS DE ÉXITO

### Antes (Estado Actual):
- Tiempo de carga inicial: **5+ segundos**
- Cache hits: **0%** (MemoryCache no funciona)
- Peticiones simultáneas: **17**
- Queries a BD por carga: **17+ queries complejas**

### Después (Fase 1 - Redis):
- Tiempo de carga inicial: **5 segundos** (primera vez)
- Tiempo de carga siguiente: **<500ms** (cache HIT)
- Cache hits: **>90%** después de primera carga
- Peticiones simultáneas: **17** (igual, pero con cache)
- Queries a BD por carga: **17** (solo primera vez, luego 0)

### Después (Fase 2 - Optimización Frontend):
- Tiempo de carga inicial: **2-3 segundos** (carga progresiva)
- KPIs visibles en: **<1 segundo**
- Peticiones simultáneas: **3-5** (batches)
- Queries a BD por carga: **3-5** (solo primera vez)

### Después (Fase 3 - Query Batching):
- Tiempo de carga inicial: **2 segundos** (una sola petición)
- Cache hits: **>95%**
- Peticiones simultáneas: **1**
- Queries a BD por carga: **1 batch optimizado**

---

## 🚨 PRIORIDADES

### **CRÍTICO (Hacer Hoy):**
1. ✅ Configurar Redis en Render
2. ✅ Aumentar TTL del cache

### **IMPORTANTE (Esta Semana):**
3. ✅ Optimizar carga del frontend

### **MEJORA (Próximas 2 Semanas):**
4. ⏳ Query Batching

---

## 📝 NOTAS ADICIONALES

### ¿Por qué MemoryCache no funciona en producción?

**Gunicorn con múltiples workers:**
```
Worker 1: MemoryCache (vacío)
Worker 2: MemoryCache (vacío)
Worker 3: MemoryCache (vacío)
```

**Flujo sin Redis:**
1. Usuario hace petición → Worker 1
2. Worker 1: Cache MISS → Calcula → Guarda en su MemoryCache
3. Usuario hace petición → Worker 2 (diferente worker)
4. Worker 2: Cache MISS → Calcula → Guarda en su MemoryCache
5. **Resultado:** Cada worker calcula todo independientemente

**Flujo con Redis:**
1. Usuario hace petición → Worker 1
2. Worker 1: Cache MISS → Calcula → Guarda en Redis
3. Usuario hace petición → Worker 2
4. Worker 2: Cache HIT → Obtiene de Redis → Respuesta instantánea
5. **Resultado:** Todos los workers comparten el mismo cache

---

## ✅ CONCLUSIÓN

El problema principal es que **Redis no está configurado en producción**, lo que causa que el cache no funcione entre múltiples workers. Esto resulta en:

- **5+ segundos** de tiempo de respuesta
- **17 queries simultáneas** a la BD
- **0% de cache hits** efectivos
- **Saturación de la base de datos**

**La solución inmediata es configurar Redis**, lo que debería reducir el tiempo de respuesta en **80-95%** para cargas subsecuentes.

---

**Generado:** 2025-11-06  
**Estado:** Análisis Completo - Listo para Implementación

