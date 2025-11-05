# 📋 GUÍA: ACTUALIZAR CÁLCULOS DE MOROSIDAD

## 🎯 OBJETIVO
Actualizar los cálculos de morosidad para KPIs usando el campo `monto_pagado` de la tabla `pagos`.

## 📝 ORDEN DE EJECUCIÓN

### **PASO 1: Verificar datos** ⚠️ OBLIGATORIO
**Script:** `scripts/sql/VERIFICAR_TOTAL_PAGADO_REAL.sql`

**Qué hace:**
- Verifica el total de `monto_pagado` en la tabla `pagos`
- Muestra pagos con y sin `prestamo_id`
- Compara diferentes métodos de cálculo

**Ejecutar:**
```sql
-- Abrir y ejecutar: scripts/sql/VERIFICAR_TOTAL_PAGADO_REAL.sql
```

**Resultado esperado:**
- Total pagado: $1,529,520
- 13,679 registros activos con pago

---

### **PASO 2: Calcular morosidad** ✅ PRINCIPAL
**Script:** `scripts/sql/CALCULAR_MOROSIDAD_KPIS.sql`

**Qué hace:**
1. **Días de morosidad por persona** - Compara `fecha_pago` vs `fecha_vencimiento`
2. **Días de morosidad por persona y mes** - Evolución mensual
3. **Dinero no cobrado por mes** - `monto_cuota` (programado) vs `monto_pagado` (real)
4. **Dinero no cobrado por persona y mes** - Detalle por cliente
5. **Resumen general para KPIs** - Métricas consolidadas

**Ejecutar:**
```sql
-- Abrir y ejecutar: scripts/sql/CALCULAR_MOROSIDAD_KPIS.sql
-- Ejecuta todas las secciones o solo las que necesites
```

**Resultado esperado:**
- `total_pagado_real` debe mostrar los valores correctos usando `monto_pagado`
- Incluye pagos con y sin `prestamo_id`

---

### **PASO 3: Actualizar tablas oficiales** (Opcional)
**Script:** `scripts/sql/ACTUALIZAR_CALCULOS_MOROSIDAD.sql`

**Qué hace:**
- Actualiza la tabla `dashboard_morosidad_mensual` si existe
- Solo ejecutar si usas las tablas oficiales del dashboard

**Ejecutar:**
```sql
-- Solo si necesitas actualizar tablas oficiales
-- scripts/sql/ACTUALIZAR_CALCULOS_MOROSIDAD.sql
```

---

## ⚠️ NOTA IMPORTANTE

**Situación actual:**
- Todos los 13,679 pagos tienen `prestamo_id = NULL`
- Por lo tanto, no se relacionan directamente con cuotas
- El script ahora usa `fecha_pago` del pago cuando no hay `prestamo_id`

**Solución implementada:**
- Si el pago tiene `prestamo_id`: relaciona con cuotas y usa mes de vencimiento
- Si el pago NO tiene `prestamo_id`: usa mes de `fecha_pago` del pago

---

## 📊 RESUMEN DE SCRIPTS

| Script | Cuándo ejecutar | Para qué |
|--------|----------------|----------|
| `VERIFICAR_TOTAL_PAGADO_REAL.sql` | Primero | Verificar datos |
| `CALCULAR_MOROSIDAD_KPIS.sql` | Segundo | Calcular métricas |
| `ACTUALIZAR_CALCULOS_MOROSIDAD.sql` | Opcional | Actualizar tablas oficiales |

---

## ✅ RECOMENDACIÓN

**Para actualizar los cálculos de morosidad:**

1. ✅ Ejecuta: `VERIFICAR_TOTAL_PAGADO_REAL.sql` (verificar)
2. ✅ Ejecuta: `CALCULAR_MOROSIDAD_KPIS.sql` (calcular)

**Eso es todo.** Los cálculos ya están usando `monto_pagado` de la tabla `pagos`.

