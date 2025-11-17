# 📊 EXPLICACIÓN DETALLADA: CÓMO SE CALCULA LA MOROSIDAD

**Fecha:** 2025-01-04
**Endpoint:** `/api/v1/dashboard/evolucion-morosidad`

---

## 🎯 RESUMEN EJECUTIVO

La morosidad se calcula sumando el `monto_cuota` de todas las cuotas que:
1. ✅ Pertenecen a préstamos **APROBADOS**
2. ✅ Tienen `fecha_vencimiento` **menor a la fecha actual** (vencidas)
3. ✅ Tienen `estado != 'PAGADO'` (no pagadas)
4. ✅ Se agrupan por **mes y año** de su fecha de vencimiento

---

## 📋 PASO A PASO DEL CÁLCULO

### **PASO 1: Calcular el Rango de Fechas**

```python
# Líneas 2417-2423
hoy = date.today()  # Ejemplo: 2025-01-04
meses = 6  # Por defecto, últimos 6 meses

# Calcular fecha inicio (hace N meses)
año_inicio = hoy.year  # 2025
mes_inicio = hoy.month - meses + 1  # 1 - 6 + 1 = -4 → Ajustar
if mes_inicio <= 0:
    año_inicio -= 1  # 2024
    mes_inicio += 12  # -4 + 12 = 8
fecha_inicio_query = date(año_inicio, mes_inicio, 1)  # 2024-08-01
```

**Ejemplo:**
- Si hoy es **4 de Enero 2025** y queremos **6 meses**:
  - Fecha inicio: **1 de Agosto 2024**
  - Fecha fin: **4 de Enero 2025**

---

### **PASO 2: Construir los Filtros Base**

```python
# Líneas 2427-2432
filtros_base = [
    "p.estado = 'APROBADO'",                    # Solo préstamos aprobados
    "c.fecha_vencimiento >= :fecha_inicio",      # Desde fecha inicio
    "c.fecha_vencimiento < :fecha_fin_total",    # Hasta hoy (sin incluir)
    "c.estado != 'PAGADO'",                      # Solo cuotas NO pagadas
]
```

**Significado de cada filtro:**

1. **`p.estado = 'APROBADO'`**
   - Solo cuenta préstamos que están aprobados
   - Excluye préstamos en borrador, rechazados, etc.

2. **`c.fecha_vencimiento >= :fecha_inicio`**
   - Solo cuotas que vencieron en el rango de meses solicitado
   - Ejemplo: Desde Agosto 2024

3. **`c.fecha_vencimiento < :fecha_fin_total`**
   - Solo cuotas que vencieron antes de hoy
   - No cuenta cuotas futuras

4. **`c.estado != 'PAGADO'`**
   - ⚠️ **CRÍTICO:** Solo cuenta cuotas que NO están pagadas
   - Si una cuota tiene `estado = 'PAGADO'`, NO se suma a la morosidad

---

### **PASO 3: Aplicar Filtros Opcionales**

```python
# Líneas 2439-2448
if analista:
    filtros_base.append("(p.analista = :analista OR p.producto_financiero = :analista)")
if concesionario:
    filtros_base.append("p.concesionario = :concesionario")
if modelo:
    filtros_base.append("(p.producto = :modelo OR p.modelo_vehiculo = :modelo)")
```

**Filtros adicionales:**
- Si se especifica un analista, solo cuenta préstamos de ese analista
- Si se especifica un concesionario, solo cuenta préstamos de ese concesionario
- Si se especifica un modelo, solo cuenta préstamos de ese modelo

---

### **PASO 4: Ejecutar la Query SQL**

```sql
-- Líneas 2453-2467
SELECT
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento >= '2024-08-01'
    AND c.fecha_vencimiento < '2025-01-04'
    AND c.estado != 'PAGADO'
GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
ORDER BY año, mes
```

**¿Qué hace esta query?**

1. **JOIN:** Conecta `cuotas` con `prestamos` para acceder a los datos del préstamo
2. **FILTROS:** Aplica todos los filtros construidos
3. **EXTRACT:** Extrae el año y mes de `fecha_vencimiento`
4. **SUM:** Suma todos los `monto_cuota` que cumplen las condiciones
5. **GROUP BY:** Agrupa por año y mes
6. **ORDER BY:** Ordena cronológicamente

**Resultado de la query:**
```
año  | mes | morosidad
-----|-----|----------
2024 |  8  | 65000.00
2024 |  9  | 72000.00
2024 | 10  | 90000.00
2024 | 11  | 115000.00
2024 | 12  | 5000.00
```

---

### **PASO 5: Convertir Resultados a Diccionario**

```python
# Línea 2470
result = db.execute(query_sql)
morosidad_por_mes = {
    (int(row[0]), int(row[1])): float(row[2] or Decimal("0"))
    for row in result
}
```

**Ejemplo de resultado:**
```python
morosidad_por_mes = {
    (2024, 8): 65000.0,
    (2024, 9): 72000.0,
    (2024, 10): 90000.0,
    (2024, 11): 115000.0,
    (2024, 12): 5000.0,
}
```

**Clave:** `(año, mes)` como tupla
**Valor:** `morosidad` como float

---

### **PASO 6: Generar Datos Mensuales (Incluyendo Meses Sin Datos)**

```python
# Líneas 2472-2489
meses_data = []
current_date = fecha_inicio_query  # 2024-08-01
nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

while current_date <= hoy:  # Mientras no lleguemos a hoy
    año_mes = current_date.year  # 2024
    num_mes = current_date.month  # 8

    # Buscar morosidad en el diccionario, si no existe = 0.0
    morosidad_mes = morosidad_por_mes.get((año_mes, num_mes), 0.0)

    meses_data.append({
        "mes": f"{nombres_meses[num_mes - 1]} {año_mes}",  # "Ago 2024"
        "morosidad": morosidad_mes,  # 65000.0
    })

    # Avanzar al siguiente mes
    current_date = _obtener_fechas_mes_siguiente(num_mes, año_mes)
```

**¿Por qué este paso?**

La query SQL solo retorna meses que tienen morosidad. Pero el gráfico necesita mostrar **todos los meses** del rango, incluso si no hay morosidad (mostrar 0).

**Ejemplo de resultado final:**
```python
meses_data = [
    {"mes": "Ago 2024", "morosidad": 65000.0},
    {"mes": "Sep 2024", "morosidad": 72000.0},
    {"mes": "Oct 2024", "morosidad": 90000.0},
    {"mes": "Nov 2024", "morosidad": 115000.0},
    {"mes": "Dic 2024", "morosidad": 5000.0},
    {"mes": "Ene 2025", "morosidad": 0.0},  # Mes sin datos = 0.0
]
```

---

## 🔍 EJEMPLO PRÁCTICO COMPLETO

### **Escenario:**
- Fecha actual: **4 de Enero 2025**
- Meses solicitados: **6 meses**
- Datos en la base de datos:

| Cuota ID | Prestamo | Fecha Vencimiento | Estado    | Monto Cuota |
|----------|----------|------------------|-----------|-------------|
| 1        | 100      | 2024-08-15       | PENDIENTE | 5000        |
| 2        | 100      | 2024-08-15       | PAGADO    | 3000        |
| 3        | 101      | 2024-09-20       | PENDIENTE | 7000        |
| 4        | 102      | 2024-10-10       | PENDIENTE | 9000        |
| 5        | 103      | 2024-11-05       | PENDIENTE | 11500       |
| 6        | 104      | 2024-12-01       | PAGADO    | 2000        |
| 7        | 105      | 2025-01-10       | PENDIENTE | 4000        |

### **Proceso de Cálculo:**

#### **1. Filtros aplicados:**
- ✅ `p.estado = 'APROBADO'` → Todos los préstamos aprobados
- ✅ `c.fecha_vencimiento >= 2024-08-01` → Desde Agosto
- ✅ `c.fecha_vencimiento < 2025-01-04` → Hasta hoy
- ✅ `c.estado != 'PAGADO'` → Excluir cuotas pagadas

#### **2. Cuotas que cumplen:**
- ✅ Cuota 1: Agosto 2024, PENDIENTE → **$5,000**
- ❌ Cuota 2: Agosto 2024, PAGADO → **NO cuenta**
- ✅ Cuota 3: Septiembre 2024, PENDIENTE → **$7,000**
- ✅ Cuota 4: Octubre 2024, PENDIENTE → **$9,000**
- ✅ Cuota 5: Noviembre 2024, PENDIENTE → **$11,500**
- ❌ Cuota 6: Diciembre 2024, PAGADO → **NO cuenta**
- ✅ Cuota 7: Enero 2025, PENDIENTE → **PERO** fecha_vencimiento (2025-01-10) > hoy (2025-01-04) → **NO cuenta** (aún no vence)

#### **3. Resultado agrupado por mes:**
```
Ago 2024:  $5,000  (solo cuota 1)
Sep 2024:  $7,000  (solo cuota 3)
Oct 2024:  $9,000  (solo cuota 4)
Nov 2024:  $11,500 (solo cuota 5)
Dic 2024:  $0      (cuota 6 está pagada, no cuenta)
Ene 2025:  $0      (cuota 7 aún no vence)
```

#### **4. Resultado final:**
```json
{
  "meses": [
    {"mes": "Ago 2024", "morosidad": 5000.0},
    {"mes": "Sep 2024", "morosidad": 7000.0},
    {"mes": "Oct 2024", "morosidad": 9000.0},
    {"mes": "Nov 2024", "morosidad": 11500.0},
    {"mes": "Dic 2024", "morosidad": 0.0},
    {"mes": "Ene 2025", "morosidad": 0.0}
  ]
}
```

---

## ⚠️ PUNTOS CRÍTICOS DEL CÁLCULO

### **1. ¿Qué es "Morosidad"?**

**Morosidad = Suma de montos de cuotas vencidas que NO están pagadas**

- ✅ **Cuenta:** Cuotas con `estado != 'PAGADO'` y `fecha_vencimiento < hoy`
- ❌ **No cuenta:** Cuotas con `estado = 'PAGADO'` (aunque hayan vencido)
- ❌ **No cuenta:** Cuotas con `fecha_vencimiento >= hoy` (aún no vencen)

### **2. ¿Por qué se agrupa por mes de vencimiento?**

Porque queremos ver **cuánta morosidad se generó cada mes**, no cuánto se acumuló.

**Ejemplo:**
- Si en Agosto vencieron $5,000 y no se pagaron
- Y en Septiembre vencieron $7,000 más y tampoco se pagaron
- La morosidad de Agosto sigue siendo $5,000 (solo cuenta las que vencieron en Agosto)
- La morosidad de Septiembre es $7,000 (solo cuenta las que vencieron en Septiembre)

### **3. ¿Por qué no se consulta tabla de cobros?**

Porque la morosidad se determina **únicamente** por el estado de la cuota:
- Si `cuota.estado = 'PAGADO'` → No es morosidad
- Si `cuota.estado != 'PAGADO'` → Es morosidad

No importa si hay un registro de cobro en otra tabla. Lo único que importa es el estado de la cuota.

---

## 📊 FÓRMULA FINAL

```
MOROSIDAD_MES = SUM(monto_cuota)
                WHERE:
                  - prestamo.estado = 'APROBADO'
                  - cuota.fecha_vencimiento >= fecha_inicio
                  - cuota.fecha_vencimiento < fecha_actual
                  - cuota.estado != 'PAGADO'
                GROUP BY:
                  - EXTRACT(YEAR FROM cuota.fecha_vencimiento)
                  - EXTRACT(MONTH FROM cuota.fecha_vencimiento)
```

---

## ✅ RESUMEN

**El cálculo de morosidad es:**

1. **Simple:** Solo suma montos de cuotas no pagadas
2. **Directo:** Solo consulta tabla `cuotas` y `prestamos`
3. **Basado en estado:** Usa `cuota.estado != 'PAGADO'` como único criterio
4. **Agrupado por mes:** Muestra cuánta morosidad se generó cada mes
5. **Incluye meses sin datos:** Muestra 0.0 para meses sin morosidad

**NO depende de:**
- ❌ Tablas de cobros
- ❌ Tablas de pagos realizados
- ❌ Cálculos complejos
- ❌ Otros sistemas

---

**Documento generado automáticamente**
**Última actualización:** 2025-01-04

