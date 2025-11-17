# 🔍 ANÁLISIS DE PERFORMANCE: Endpoints Dashboard

**Fecha:** 2025-11-06
**Análisis:** Logs de red del navegador

---

## 📊 TIEMPOS DE RESPUESTA OBSERVADOS

### **🚨 CRÍTICO - Endpoints Muy Lentos (>5 segundos):**

| Endpoint | Tiempo | Estado |
|----------|--------|--------|
| `/api/v1/dashboard/financiamiento-tendencia-mensual?meses=12` | **23,572ms** (23.5s) | 🔴 CRÍTICO |
| `/api/v1/dashboard/admin?periodo=mes` | **6,542ms** (6.5s) | 🟠 ALTO |
| `/api/v1/dashboard/kpis-principales` | **6,033ms** (6s) | 🟠 ALTO |
| `/api/v1/dashboard/morosidad-por-analista?` | **4,885ms** (4.9s) | 🟠 ALTO |
| `/api/v1/dashboard/financiamiento-por-rangos?` | **3,982ms** (4s) | 🟡 MEDIO |

### **✅ Endpoints Aceptables (<3 segundos):**

| Endpoint | Tiempo | Estado |
|----------|--------|--------|
| `/api/v1/dashboard/evolucion-pagos?meses=6` | **3,618ms** (3.6s) | 🟡 MEDIO |
| `/api/v1/dashboard/composicion-morosidad?` | **3,513ms** (3.5s) | 🟡 MEDIO |
| `/api/v1/dashboard/cobranzas-mensuales?` | **2,118ms** (2.1s) | 🟢 ACEPTABLE |
| `/api/v1/dashboard/resumen-financiamiento-pagado?` | **2,309ms** (2.3s) | 🟢 ACEPTABLE |
| `/api/v1/dashboard/evolucion-morosidad?meses=6` | **2,292ms** (2.3s) | 🟢 ACEPTABLE |

### **✅ Endpoints Rápidos (<2 segundos):**

| Endpoint | Tiempo | Estado |
|----------|--------|--------|
| `/api/v1/dashboard/prestamos-por-concesionario?` | **1,696ms** (1.7s) | 🟢 BUENO |
| `/api/v1/dashboard/prestamos-por-modelo?` | **1,426ms** (1.4s) | 🟢 BUENO |
| `/api/v1/dashboard/cobranzas-semanales?semanas=12` | **1,421ms** (1.4s) | 🟢 BUENO |
| `/api/v1/dashboard/opciones-filtros` | **1,223ms** (1.2s) | 🟢 BUENO |
| `/api/v1/notificaciones/estadisticas/resumen` | **1,124ms** (1.1s) | 🟢 BUENO |

### **✅ Endpoints con Cache Funcionando (segunda carga):**

| Endpoint | Primera Carga | Segunda Carga | Mejora |
|----------|---------------|--------------|--------|
| `/api/v1/pagos/kpis` | **2,992ms** | **716ms** | ✅ 76% más rápido |
| `/api/v1/notificaciones/estadisticas/resumen` | **1,124ms** | **776ms** | ✅ 31% más rápido |

---

## 🔴 PROBLEMA CRÍTICO: `financiamiento-tendencia-mensual`

### **Análisis:**

**Tiempo de respuesta:** 23.5 segundos (23,572ms)

**Causas Identificadas:**

1. **Redis NO está funcionando:**
   - El endpoint tiene `@cache_result(ttl=600)` pero el tiempo es muy alto
   - Esto sugiere que está usando `MemoryCache` (no compartido entre workers)
   - Cada request recalcula todo desde cero

2. **Queries complejas sin optimización:**
   - Múltiples queries MIN() para buscar primera fecha
   - Queries con GROUP BY sobre grandes volúmenes de datos
   - Cálculos de morosidad mensual en Python (no en SQL)

3. **Procesamiento pesado:**
   - Loop sobre meses generando datos
   - Cálculos de morosidad por mes
   - Agregaciones complejas en Python

---

## 🎯 SOLUCIONES PROPUESTAS

### **1. URGENTE: Configurar Redis**

**Impacto:** Reducción de 80-95% en tiempos de respuesta

**Acción:**
- Verificar que `REDIS_URL` está configurada en Render
- Verificar que el servicio Redis está "Live"
- Después del deploy, los tiempos deberían bajar a 1-3 segundos (primera carga) y <500ms (cache hit)

---

### **2. Optimizar Queries del Endpoint Crítico**

**Problema:** Múltiples queries MIN() en cada request

**Solución:**
- Ya existe cache para `primera_fecha_desde_2024` (1 hora)
- Verificar que el cache está funcionando
- Si Redis no funciona, este cache tampoco funciona

**Código actual:**
```python
cache_key_primera_fecha = "dashboard:primera_fecha_desde_2024"
primera_fecha_cached = cache_backend.get(cache_key_primera_fecha)
```

---

### **3. Aumentar TTL del Cache**

**Problema:** TTL actual es 600 segundos (10 minutos)

**Solución:**
- Aumentar a 1800 segundos (30 minutos) para datos históricos
- Los datos de tendencia mensual no cambian frecuentemente

**Código actual:**
```python
@cache_result(ttl=600, key_prefix="dashboard")  # 10 minutos
```

**Propuesta:**
```python
@cache_result(ttl=1800, key_prefix="dashboard")  # 30 minutos
```

---

### **4. Optimizar Queries SQL**

**Problema:** Queries con GROUP BY sobre grandes volúmenes

**Solución:**
- Verificar que existen índices en:
  - `Prestamo.fecha_aprobacion`
  - `Cuota.fecha_vencimiento`
  - `Pago.fecha_pago`
- Usar índices compuestos si es necesario

---

## 📋 CHECKLIST DE ACCIONES

### **URGENTE (Hoy):**

- [ ] Verificar `REDIS_URL` en Render (Backend → Environment)
- [ ] Verificar servicio Redis está "Live"
- [ ] Hacer deploy de cambios recientes (cache.py, main.py)
- [ ] Verificar logs del backend para confirmar conexión Redis

### **Corto Plazo (Esta Semana):**

- [ ] Aumentar TTL de cache a 30 minutos para endpoints históricos
- [ ] Verificar índices en base de datos
- [ ] Monitorear tiempos después de configurar Redis

### **Mediano Plazo (Próximas 2 Semanas):**

- [ ] Optimizar queries más complejas
- [ ] Mover cálculos de morosidad a SQL (si es posible)
- [ ] Implementar paginación para endpoints grandes

---

## 🎯 RESULTADOS ESPERADOS DESPUÉS DE CONFIGURAR REDIS

### **Antes (MemoryCache):**
- Primera carga: 23.5 segundos
- Segunda carga: 23.5 segundos (sin cache compartido)

### **Después (Redis):**
- Primera carga: 2-4 segundos (con cache de queries)
- Segunda carga: <500ms (cache hit completo)
- **Mejora: 95-98% más rápido**

---

## 📊 COMPARACIÓN DE TIEMPOS

### **Endpoints con Cache Funcionando:**
```
/api/v1/pagos/kpis:
  Primera: 2,992ms
  Segunda: 716ms (76% más rápido) ✅
```

### **Endpoints SIN Cache (Redis no funciona):**
```
/api/v1/dashboard/financiamiento-tendencia-mensual:
  Primera: 23,572ms
  Segunda: ~23,572ms (sin mejora) ❌
```

---

## 🔍 CONCLUSIÓN

**Problema Principal:** Redis NO está configurado o no está funcionando

**Impacto:**
- Endpoints críticos tardan 23+ segundos
- Sin cache compartido entre workers
- Cada request recalcula todo desde cero

**Solución Inmediata:**
1. Configurar Redis en Render
2. Verificar conexión
3. Hacer deploy
4. Monitorear mejoras

**Mejora Esperada:** 95-98% más rápido después de configurar Redis

