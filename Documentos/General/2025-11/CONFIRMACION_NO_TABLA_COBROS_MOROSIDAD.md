# ✅ CONFIRMACIÓN: NO SE CONSULTA TABLA DE COBROS PARA MOROSIDAD

**Fecha:** 2025-01-04  
**Endpoint:** `/api/v1/dashboard/evolucion-morosidad`

---

## 📋 RESUMEN

El endpoint de **Evolución de Morosidad** **NO consulta ninguna tabla de "cobros"**, "pagos realizados", "cobros realizados" o similar. 

**Solo consulta:**
- ✅ Tabla `cuotas` (campo `estado` y `monto_cuota`)
- ✅ Tabla `prestamos` (solo para filtros de estado)

---

## 🔍 QUERY ACTUAL (CORRECTA)

### **Tablas Consultadas:**

```sql
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
```

**✅ Solo 2 tablas:**
1. `cuotas` - Para obtener el monto y estado de cada cuota
2. `prestamos` - Solo para validar que el préstamo esté `APROBADO`

### **Criterio de Morosidad:**

```sql
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento >= :fecha_inicio
    AND c.fecha_vencimiento < :fecha_fin_total
    AND c.estado != 'PAGADO'  ← SOLO USA ESTE CAMPO
```

**✅ La morosidad se determina ÚNICAMENTE por:**
- `cuota.estado != 'PAGADO'` ← **NO consulta tabla de cobros**
- `cuota.fecha_vencimiento < fecha_actual` ← Cuotas vencidas

---

## ✅ CONFIRMACIÓN DE CÓDIGO

### **Backend - Endpoint Completo:**

```python
# backend/app/api/v1/endpoints/dashboard.py (líneas 2452-2467)

query_sql = text(
    """
    SELECT 
        EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
        EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
        COALESCE(SUM(c.monto_cuota), 0) as morosidad
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE 
        p.estado = 'APROBADO'
        AND c.fecha_vencimiento >= :fecha_inicio
        AND c.fecha_vencimiento < :fecha_fin_total
        AND c.estado != 'PAGADO'
    GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
    ORDER BY año, mes
"""
)
```

### **Tablas NO Consultadas:**

❌ **NO consulta:**
- `pagos_staging`
- `pagos_realizados`
- `cobros`
- `cobros_realizados`
- `pagos`
- Cualquier otra tabla relacionada con cobros/pagos realizados

---

## 📊 CÁLCULO DE MOROSIDAD

### **Definición Correcta:**

La morosidad se calcula **exclusivamente** basándose en:

1. **Estado de la cuota:** `cuota.estado != 'PAGADO'`
   - Si la cuota tiene `estado = 'PAGADO'` → **NO es morosidad**
   - Si la cuota tiene `estado != 'PAGADO'` → **ES morosidad**

2. **Fecha de vencimiento:** `cuota.fecha_vencimiento < fecha_actual`
   - Solo cuotas que ya vencieron

3. **Estado del préstamo:** `prestamo.estado = 'APROBADO'`
   - Solo préstamos aprobados

### **NO se considera:**
- ❌ Si hay un registro de cobro en otra tabla
- ❌ Si hay un pago registrado en `pagos_staging`
- ❌ Si hay un registro en tabla de "cobros realizados"
- ❌ Cualquier otra tabla externa

---

## 🔍 VERIFICACIÓN

### **Cómo verificar que NO se consulta tabla de cobros:**

1. **Buscar en el código:**
   ```bash
   grep -r "pagos_staging\|cobros\|pagos_realizados" backend/app/api/v1/endpoints/dashboard.py
   ```
   - Debe retornar **0 resultados** en el endpoint `evolucion-morosidad`

2. **Revisar la query SQL:**
   - La query solo debe tener `FROM cuotas` y `JOIN prestamos`
   - No debe tener ningún `JOIN` con tablas de cobros/pagos

3. **Verificar filtros:**
   - Solo debe usar `c.estado != 'PAGADO'`
   - No debe consultar otra tabla para verificar si se cobró

---

## 📝 CONCLUSIÓN

✅ **CONFIRMADO:** El endpoint de Evolución de Morosidad:

1. ✅ **NO consulta** tabla de cobros
2. ✅ **NO consulta** tabla de pagos realizados
3. ✅ **Solo consulta** `cuotas` y `prestamos`
4. ✅ **Usa únicamente** el campo `cuota.estado != 'PAGADO'` para determinar morosidad
5. ✅ **No depende** de ninguna tabla externa de cobros/pagos

**El cálculo de morosidad es independiente de cualquier registro de cobro/pago en otras tablas.**

---

**Documento generado automáticamente**  
**Última actualización:** 2025-01-04

