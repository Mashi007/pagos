# 🔍 VERIFICACIÓN: Índices Existentes vs Nuevos

**Fecha:** 2025-01-27  
**Análisis:** Comparación de índices existentes vs índices agregados en optimización

---

## ✅ ÍNDICES QUE YA EXISTEN (No necesitan crearse)

### Tabla `prestamos`:
1. ✅ `idx_prestamos_estado` - Ya existe en migración `20251104_add_critical_performance_indexes.py`
2. ✅ `idx_prestamos_cedula` - Ya existe en migración `20251104_add_critical_performance_indexes.py`
3. ✅ `idx_prestamos_aprobacion_estado_analista` - Ya existe en `migracion_indices_dashboard.sql`
4. ✅ `idx_prestamos_cedula_estado` - Ya existe en `migracion_indices_dashboard.sql`
5. ✅ `idx_prestamos_concesionario_estado` - Ya existe en `migracion_indices_dashboard.sql`
6. ✅ `idx_prestamos_modelo_estado` - Ya existe en `migracion_indices_dashboard.sql`

### Tabla `cuotas`:
1. ✅ `idx_cuotas_vencimiento_estado` - Ya existe en migración `20251104_add_critical_performance_indexes.py`
2. ✅ `idx_cuotas_prestamo_id` - Ya existe en migración `20251104_add_critical_performance_indexes.py`
3. ✅ `idx_cuotas_fecha_vencimiento_ym` - Ya existe en `migracion_indices_dashboard.sql`
4. ✅ `idx_cuotas_prestamo_fecha_vencimiento` - Ya existe en `migracion_indices_dashboard.sql`

### Tabla `pagos`:
1. ✅ `idx_pagos_fecha_pago_activo` - Ya existe en `migracion_indices_dashboard.sql` (línea 75)
2. ✅ `idx_pagos_prestamo_fecha` - Ya existe en `migracion_indices_dashboard.sql` (línea 84)

---

## 🆕 ÍNDICES NUEVOS (Agregados en optimización Prioridad 1)

### Tabla `prestamos`:
1. 🆕 `idx_prestamos_estado_fecha_aprobacion` - **NUEVO**
   - Campos: `(estado, fecha_aprobacion)`
   - Uso: Optimiza queries que filtran por estado y fecha_aprobacion simultáneamente
   - **¿Necesario?** ✅ SÍ - Mejora queries en `/dashboard/kpis-principales`

2. 🆕 `idx_prestamos_estado_fecha_registro` - **NUEVO**
   - Campos: `(estado, fecha_registro)`
   - Uso: Optimiza queries que filtran por estado y fecha_registro simultáneamente
   - **¿Necesario?** ✅ SÍ - Mejora queries en `/dashboard/kpis-principales` (mes anterior)

### Tabla `pagos`:
3. 🆕 `idx_pagos_fecha_pago_monto` - **NUEVO**
   - Campos: `(fecha_pago, monto_pagado)`
   - Uso: Optimiza queries que filtran por fecha y suman montos
   - **¿Necesario?** ⚠️ PARCIAL - Similar a `idx_pagos_fecha_pago_activo` pero sin filtro `activo`
   - **Nota:** Ya existe `idx_pagos_fecha_pago_activo` con `(fecha_pago, activo, monto_pagado)`

### Tabla `pagos_staging`:
4. 🆕 `idx_pagos_staging_fecha_monto` - **NUEVO**
   - Campos: `(fecha_pago, monto_pagado)` con WHERE parcial
   - Uso: Optimiza queries en `/dashboard/admin` que usan `pagos_staging`
   - **¿Necesario?** ✅ SÍ - Si se usa `pagos_staging` en producción

---

## 📊 RESUMEN

| Índice | Estado | Acción |
|--------|--------|--------|
| `idx_prestamos_estado_fecha_aprobacion` | 🆕 NUEVO | ✅ **CREAR** - Mejora kpis-principales |
| `idx_prestamos_estado_fecha_registro` | 🆕 NUEVO | ✅ **CREAR** - Mejora kpis-principales |
| `idx_pagos_fecha_pago_monto` | 🆕 NUEVO | ⚠️ **OPCIONAL** - Similar a existente |
| `idx_pagos_staging_fecha_monto` | 🆕 NUEVO | ✅ **CREAR** - Si se usa pagos_staging |

---

## ✅ CONCLUSIÓN

**Los índices que agregué en `crear_indices_manual.py` son:**

1. **2 índices nuevos importantes** para `prestamos`:
   - `idx_prestamos_estado_fecha_aprobacion`
   - `idx_prestamos_estado_fecha_registro`
   - **Estos SÍ mejoran el rendimiento** de `/dashboard/kpis-principales`

2. **1 índice nuevo para `pagos_staging`**:
   - `idx_pagos_staging_fecha_monto`
   - **Solo necesario si se usa `pagos_staging` en producción**

3. **1 índice redundante**:
   - `idx_pagos_fecha_pago_activo` - Ya existe en `migracion_indices_dashboard.sql`
   - El script lo omite automáticamente con `IF NOT EXISTS`

---

## 🎯 RECOMENDACIÓN

**El script `crear_indices_manual.py` es seguro de ejecutar porque:**
- ✅ Usa `CREATE INDEX IF NOT EXISTS` - No crea índices duplicados
- ✅ Verifica existencia antes de crear
- ✅ Solo crea los índices nuevos que realmente mejoran performance

**Los índices nuevos que SÍ mejoran performance:**
- `idx_prestamos_estado_fecha_aprobacion` - **CRÍTICO** para kpis-principales
- `idx_prestamos_estado_fecha_registro` - **CRÍTICO** para kpis-principales

**Puedes ejecutar el script sin problemas** - Solo creará los índices que no existen.

