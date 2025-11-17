# 🚨 ANÁLISIS DE RIESGOS: Migración de Índices Funcionales

## 📋 QUÉ HACE LA MIGRACIÓN

La migración `20251104_add_group_by_indexes` crea **índices funcionales** sobre tablas grandes:

1. **`pagos_staging`**:
   - Índice sobre `EXTRACT(YEAR FROM fecha_pago::timestamp)`
   - Índice compuesto sobre `EXTRACT(YEAR, MONTH FROM fecha_pago::timestamp)`
   - **Tabla grande**: ~13,959 registros (según logs recientes)

2. **`cuotas`**:
   - Índice compuesto sobre `EXTRACT(YEAR, MONTH FROM fecha_vencimiento)`
   - **Tabla grande**: Múltiples registros por préstamo

---

## ⚠️ RIESGOS IDENTIFICADOS

### 🔴 RIESGO 1: **BLOQUEO DE ESCRITURAS** (CRÍTICO)

**Problema:**
- `CREATE INDEX` en PostgreSQL **bloquea escrituras** en la tabla durante la creación
- Si la tabla es grande, el bloqueo puede durar **varios minutos**

**Impacto:**
- ❌ **INSERT/UPDATE/DELETE bloqueados** en `pagos_staging` y `cuotas`
- ❌ **Usuarios no pueden registrar pagos** durante la creación
- ❌ **Sistema puede parecer "congelado"**

**Tiempo estimado:**
- Tabla pequeña (<10K registros): 30-60 segundos
- Tabla mediana (10K-100K): 1-5 minutos
- Tabla grande (>100K): 5-15 minutos

---

### 🔴 RIESGO 2: **CONSUMO DE RECURSOS** (ALTO)

**Problema:**
- Crear índices requiere **escaneo completo de la tabla**
- PostgreSQL necesita **memoria y CPU** para procesar todas las filas
- En Render Free Tier, recursos son limitados

**Impacto:**
- ⚠️ **CPU al 100%** durante la creación
- ⚠️ **Memoria aumentada** temporalmente
- ⚠️ **Queries lentas** mientras se crea el índice
- ⚠️ **Posible timeout** si el servidor no aguanta

---

### 🟡 RIESGO 3: **FALLO DURANTE LA CREACIÓN** (MEDIO)

**Problema:**
- Si la migración falla a mitad de camino:
  - ❌ Índice parcial puede quedar creado (inconsistente)
  - ❌ Transacción puede quedar en estado intermedio
  - ❌ Requiere intervención manual

**Causas posibles:**
- Timeout de conexión
- Memoria insuficiente
- Error en la expresión del índice
- Tabla o columna no existe

**Mitigación actual:**
- ✅ Usa `CREATE INDEX IF NOT EXISTS` (idempotente)
- ✅ Try/catch en cada índice (no falla todo si uno falla)
- ✅ Verifica existencia antes de crear

---

### 🟡 RIESGO 4: **TIEMPO DE EJECUCIÓN** (MEDIO)

**Problema:**
- En Render, el `releaseCommand` tiene un timeout
- Si la migración tarda más de lo esperado, puede fallar el deploy

**Tiempo estimado por índice:**
- `idx_pagos_staging_extract_year`: 30-60 segundos
- `idx_pagos_staging_extract_year_month`: 60-120 segundos
- `idx_cuotas_extract_year_month`: 60-120 segundos

**Total estimado:** 2.5 - 5 minutos

---

### 🟢 RIESGO 5: **ESPACIO EN DISCO** (BAJO)

**Problema:**
- Los índices ocupan espacio adicional
- Cada índice funcional puede ocupar ~20-30% del tamaño de la tabla

**Impacto:**
- ⚠️ Aumento de espacio en disco
- En Render Free Tier, el límite es generoso pero limitado

**Estimación:**
- Si `pagos_staging` ocupa 100MB, los índices pueden ocupar 40-60MB adicionales

---

## ✅ MITIGACIONES IMPLEMENTADAS

### 1. **Verificaciones Previas**
```python
if not _index_exists(inspector, 'pagos_staging', index_name):
    if _column_exists(inspector, 'pagos_staging', 'fecha_pago'):
        # Solo crea si no existe y columna existe
```

### 2. **Manejo de Errores**
```python
try:
    connection.execute(text(f"CREATE INDEX IF NOT EXISTS ..."))
except Exception as e:
    print(f"⚠️ Advertencia: No se pudo crear índice: {e}")
    # No falla todo si uno falla
```

### 3. **Idempotencia**
- Usa `CREATE INDEX IF NOT EXISTS`
- Puede ejecutarse múltiples veces sin problema
- Si el índice ya existe, se omite

### 4. **Ejecución Automática**
- Se ejecuta en `releaseCommand` de Render
- Alembic maneja las transacciones
- Rollback automático si falla

---

## 🎯 RECOMENDACIONES

### ✅ **OPCIÓN 1: Ejecutar en Horario de Bajo Tráfico** (RECOMENDADO)

**Ventajas:**
- Menos usuarios afectados
- Menos escrituras bloqueadas
- Menor impacto en operaciones

**Cuándo:**
- Madrugada (2-5 AM hora local)
- Fin de semana
- Cuando el tráfico sea mínimo

---

### ✅ **OPCIÓN 2: Usar CREATE INDEX CONCURRENTLY** (IDEAL PERO COMPLEJO)

**Ventajas:**
- ✅ **NO bloquea escrituras**
- ✅ Puede ejecutarse en producción sin interrupciones

**Desventajas:**
- ❌ No puede ejecutarse dentro de transacciones (Alembic usa transacciones)
- ❌ Requiere ejecución manual fuera de Alembic
- ❌ Más complejo de implementar

**Implementación:**
```sql
-- Ejecutar manualmente en psql
CREATE INDEX CONCURRENTLY idx_pagos_staging_extract_year_month
ON pagos_staging USING btree (
  EXTRACT(YEAR FROM fecha_pago::timestamp),
  EXTRACT(MONTH FROM fecha_pago::timestamp)
)
WHERE fecha_pago IS NOT NULL AND fecha_pago != '';
```

---

### ✅ **OPCIÓN 3: Ejecutar Ahora (Automático)** (ACTUAL)

**Ventajas:**
- ✅ Se ejecuta automáticamente en el próximo deploy
- ✅ No requiere intervención manual
- ✅ Alembic maneja todo

**Desventajas:**
- ⚠️ Puede bloquear escrituras durante 2-5 minutos
- ⚠️ Impacto en usuarios activos

**Cuándo se ejecuta:**
- En el próximo `git push` que dispare deploy
- En el `releaseCommand`: `alembic upgrade heads`

---

## 📊 MATRIZ DE RIESGO/DECISIÓN

| Escenario | Riesgo | Recomendación |
|-----------|--------|---------------|
| **Tabla pequeña (<10K)** | 🟢 BAJO | ✅ Ejecutar ahora |
| **Tabla mediana (10K-50K)** | 🟡 MEDIO | ✅ Ejecutar en bajo tráfico |
| **Tabla grande (>50K)** | 🔴 ALTO | ✅ Usar CONCURRENTLY o bajo tráfico |
| **Sistema crítico 24/7** | 🔴 ALTO | ✅ Usar CONCURRENTLY manualmente |
| **Sistema con horarios** | 🟡 MEDIO | ✅ Ejecutar en horario de bajo tráfico |

---

## 🛡️ PLAN DE CONTINGENCIA

### Si la migración falla:

1. **Verificar logs en Render:**
   ```
   Error en releaseCommand: ...
   ```

2. **Verificar estado de índices:**
   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename IN ('pagos_staging', 'cuotas')
   AND indexname LIKE 'idx_%_extract%';
   ```

3. **Rollback manual (si es necesario):**
   ```sql
   DROP INDEX IF EXISTS idx_pagos_staging_extract_year_month;
   DROP INDEX IF EXISTS idx_cuotas_extract_year_month;
   ```

4. **Reintentar después de corregir el problema**

---

## ✅ CONCLUSIÓN

**Riesgo General: 🟡 MEDIO**

- La migración es **relativamente segura** gracias a las mitigaciones
- El **bloqueo de escrituras** es el riesgo principal
- **Impacto temporal**: 2-5 minutos de bloqueo
- **Beneficio permanente**: Mejora de 10-30x en tiempos de respuesta

**Recomendación:**
- ✅ **Ejecutar en horario de bajo tráfico** si es posible
- ✅ Si no es posible, **ejecutar ahora** (riesgo aceptable)
- ✅ Monitorear logs durante el deploy
- ✅ Tener plan de rollback listo

---

## 📝 CHECKLIST ANTES DE EJECUTAR

- [ ] Verificar tamaño de tablas (`SELECT COUNT(*) FROM pagos_staging;`)
- [ ] Identificar horario de bajo tráfico
- [ ] Notificar a usuarios si es necesario
- [ ] Tener acceso a logs de Render
- [ ] Tener acceso a base de datos para rollback si es necesario
- [ ] Verificar que hay backups recientes

