# ✅ Confirmación: "Cuotas Programadas por Mes"

## Fecha: 2025-11-05

---

## ❓ Pregunta

**¿La línea "Cuotas Programadas por Mes" cuenta cuotas o suma en dólares todos los pagos programados para el mes?**

---

## ✅ Respuesta Confirmada

**SUMA EN DÓLARES** - Suma los montos monetarios de todas las cuotas programadas que vencen en cada mes.

**NO cuenta** el número de cuotas.

---

## 📊 Evidencia del Código

### Query SQL (Línea 3372 en `dashboard.py`)

```python
func.sum(Cuota.monto_cuota).label("total_cuotas_programadas")
```

**Operación:** `SUM()` - Suma los valores
**Campo:** `monto_cuota` - Monto en dólares de cada cuota

### Query SQL Completa

```sql
SELECT 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
    SUM(c.monto_cuota) as total_cuotas_programadas  -- ✅ SUM, no COUNT
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento >= :fecha_inicio
  AND c.fecha_vencimiento <= :fecha_fin
GROUP BY 
    EXTRACT(YEAR FROM c.fecha_vencimiento),
    EXTRACT(MONTH FROM c.fecha_vencimiento)
```

---

## 📝 Explicación

### ¿Qué hace?

1. **Filtra** todas las cuotas de préstamos aprobados que vencen en el rango de fechas
2. **Agrupa** por año y mes de `fecha_vencimiento`
3. **Suma** (`SUM`) los valores de `monto_cuota` para cada mes
4. **Resultado:** Total en dólares de todos los pagos programados para ese mes

### Ejemplo

Si en enero de 2025 hay 3 cuotas que vencen:
- Cuota 1: $500.00
- Cuota 2: $750.00
- Cuota 3: $300.00

**Resultado:** `$1,550.00` (suma de montos, no 3 cuotas)

---

## 🔍 Comparación

| Operación | SQL | Resultado |
|-----------|-----|-----------|
| **Sumar montos** | `SUM(monto_cuota)` | ✅ **Esta línea usa esto** |
| **Contar cuotas** | `COUNT(*)` | ❌ No se usa |

---

## ✅ Confirmación Final

**La línea "Cuotas Programadas por Mes":**
- ✅ **SUMA** los montos en dólares (`SUM(monto_cuota)`)
- ❌ **NO cuenta** el número de cuotas (`COUNT(*)`)
- 📊 **Representa:** Total monetario de pagos programados que vencen en cada mes

---

**Estado:** ✅ Confirmado y documentado

