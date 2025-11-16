# ✅ Confirmación: Agrupación de Cuotas Programadas por Mes

## Fecha: 2025-11-05

---

## ❓ Pregunta

**¿Se suman TODAS las cuotas del mes, agrupadas por año y mes de `fecha_vencimiento`?**

---

## ✅ Respuesta Confirmada

**SÍ** - Se suman **TODAS** las cuotas que vencen en cada mes, agrupadas por año y mes de `fecha_vencimiento`.

---

## 📊 Evidencia del Código

### Query SQL (Líneas 3368-3382 en `dashboard.py`)

```python
query_cuotas = (
    db.query(
        func.extract("year", Cuota.fecha_vencimiento).label("año"),
        func.extract("month", Cuota.fecha_vencimiento).label("mes"),
        func.sum(Cuota.monto_cuota).label("total_cuotas_programadas"),
    )
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .filter(
        Prestamo.estado == "APROBADO",
        Cuota.fecha_vencimiento >= fecha_inicio_query,
        Cuota.fecha_vencimiento <= fecha_fin_query,
    )
    .group_by(func.extract("year", Cuota.fecha_vencimiento), func.extract("month", Cuota.fecha_vencimiento))
    .order_by(func.extract("year", Cuota.fecha_vencimiento), func.extract("month", Cuota.fecha_vencimiento))
)
```

### Query SQL Equivalente

```sql
SELECT 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
    SUM(c.monto_cuota) as total_cuotas_programadas
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento >= :fecha_inicio
  AND c.fecha_vencimiento <= :fecha_fin
GROUP BY 
    EXTRACT(YEAR FROM c.fecha_vencimiento),  -- ✅ Agrupa por AÑO
    EXTRACT(MONTH FROM c.fecha_vencimiento)  -- ✅ Agrupa por MES
ORDER BY año, mes
```

---

## 🔍 Confirmación de Agrupación

### 1. **Agrupación por Año**
```python
func.extract("year", Cuota.fecha_vencimiento).label("año")
```
- Extrae el **año** de `fecha_vencimiento`
- Ejemplo: `2025` de `2025-03-15`

### 2. **Agrupación por Mes**
```python
func.extract("month", Cuota.fecha_vencimiento).label("mes")
```
- Extrae el **mes** de `fecha_vencimiento`
- Ejemplo: `3` de `2025-03-15`

### 3. **GROUP BY**
```python
.group_by(
    func.extract("year", Cuota.fecha_vencimiento),
    func.extract("month", Cuota.fecha_vencimiento)
)
```
- Agrupa por **año Y mes** combinados
- Cada combinación (año, mes) es un grupo único

### 4. **SUM de Todas las Cuotas del Mes**
```python
func.sum(Cuota.monto_cuota).label("total_cuotas_programadas")
```
- **Suma TODAS** las cuotas que pertenecen al mismo grupo (año, mes)
- No cuenta, **suma los montos**

---

## 📝 Ejemplo Práctico

### Escenario: Enero 2025

**Cuotas que vencen en enero 2025:**
- Cuota 1: `fecha_vencimiento = 2025-01-05`, `monto_cuota = $500.00`
- Cuota 2: `fecha_vencimiento = 2025-01-15`, `monto_cuota = $750.00`
- Cuota 3: `fecha_vencimiento = 2025-01-28`, `monto_cuota = $300.00`
- Cuota 4: `fecha_vencimiento = 2025-01-10`, `monto_cuota = $450.00`

### Proceso de Agrupación:

1. **Extracción de año y mes:**
   - Todas tienen: `año = 2025`, `mes = 1`

2. **GROUP BY:**
   - Todas se agrupan en: `(2025, 1)`

3. **SUM:**
   - `SUM(monto_cuota)` = `$500.00 + $750.00 + $300.00 + $450.00` = **`$2,000.00`**

4. **Resultado:**
   ```python
   cuotas_por_mes[(2025, 1)] = 2000.0
   ```

---

## ✅ Confirmación Final

### ¿Se suman TODAS las cuotas del mes?

**SÍ** - Se suman **TODAS** las cuotas que tienen:
- `fecha_vencimiento` dentro del rango de fechas
- Mismo **año** (extraído de `fecha_vencimiento`)
- Mismo **mes** (extraído de `fecha_vencimiento`)
- `Prestamo.estado = 'APROBADO'`

### ¿Cómo se agrupa?

**Por año y mes de `fecha_vencimiento`:**
- **Año:** `EXTRACT(YEAR FROM fecha_vencimiento)`
- **Mes:** `EXTRACT(MONTH FROM fecha_vencimiento)`
- **GROUP BY:** Ambas extracciones juntas

### ¿Qué se suma?

**Los montos de todas las cuotas del grupo:**
- `SUM(monto_cuota)` para cada grupo (año, mes)
- **NO cuenta** cuotas, **suma** los montos en dólares

---

## 📊 Resumen

| Aspecto | Confirmación |
|----------|--------------|
| **Agrupación** | Por año y mes de `fecha_vencimiento` |
| **Operación** | `SUM(monto_cuota)` |
| **Alcance** | TODAS las cuotas que vencen en ese mes |
| **Filtros** | `Prestamo.estado = 'APROBADO'` |
| **Rango** | `fecha_vencimiento >= fecha_inicio AND fecha_vencimiento <= fecha_fin` |

---

**Estado:** ✅ Confirmado - Se suman TODAS las cuotas del mes agrupadas por año y mes de `fecha_vencimiento`

