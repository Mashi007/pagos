# 📊 FUENTE DE DATOS PARA EL CÁLCULO DE MOROSIDAD

**Fecha:** 2025-01-04
**Endpoint:** `/api/v1/dashboard/evolucion-morosidad`

---

## 🗄️ TABLAS DE BASE DE DATOS CONSULTADAS

El cálculo de morosidad consulta **SOLO 2 tablas**:

### **1. Tabla `cuotas`** (Principal)

**Ubicación en código:** `backend/app/models/amortizacion.py`
**Nombre de tabla SQL:** `cuotas`

#### **Campos Utilizados:**

| Campo | Tipo | Uso en el Cálculo | Descripción |
|-------|------|-------------------|-------------|
| `id` | Integer | - | ID único de la cuota (no se usa directamente) |
| `prestamo_id` | Integer | ✅ **JOIN** | Para conectar con tabla `prestamos` |
| `fecha_vencimiento` | Date | ✅ **FILTRO + AGRUPACIÓN** | Fecha cuando vence la cuota. Se usa para: 1) Filtrar cuotas vencidas, 2) Extraer año/mes para agrupar |
| `monto_cuota` | Numeric(12,2) | ✅ **SUMA** | Monto total de la cuota. Este es el valor que se SUMA para calcular morosidad |
| `estado` | String(20) | ✅ **FILTRO** | Estado de la cuota. Se filtra con `!= 'PAGADO'` |

#### **Campos NO Utilizados (pero existen en la tabla):**

- `numero_cuota` - No se usa
- `fecha_pago` - No se usa
- `monto_capital` - No se usa
- `monto_interes` - No se usa
- `capital_pagado` - No se usa
- `interes_pagado` - No se usa
- `mora_pagada` - No se usa
- `total_pagado` - No se usa
- `capital_pendiente` - No se usa
- `interes_pendiente` - No se usa
- `dias_mora` - No se usa
- `monto_mora` - No se usa
- `tasa_mora` - No se usa
- `observaciones` - No se usa
- `es_cuota_especial` - No se usa

---

### **2. Tabla `prestamos`** (Para filtros)

**Ubicación en código:** `backend/app/models/prestamo.py`
**Nombre de tabla SQL:** `prestamos`

#### **Campos Utilizados:**

| Campo | Tipo | Uso en el Cálculo | Descripción |
|-------|------|-------------------|-------------|
| `id` | Integer | ✅ **JOIN** | Para conectar con `cuotas.prestamo_id` |
| `estado` | String(20) | ✅ **FILTRO** | Se filtra con `= 'APROBADO'`. Solo cuenta préstamos aprobados |
| `analista` | String(100) | ⚠️ **FILTRO OPCIONAL** | Solo si se pasa filtro `analista` en la query |
| `producto_financiero` | String(100) | ⚠️ **FILTRO OPCIONAL** | Solo si se pasa filtro `analista` (alternativa) |
| `concesionario` | String(100) | ⚠️ **FILTRO OPCIONAL** | Solo si se pasa filtro `concesionario` |
| `producto` | String(100) | ⚠️ **FILTRO OPCIONAL** | Solo si se pasa filtro `modelo` |
| `modelo_vehiculo` | String(100) | ⚠️ **FILTRO OPCIONAL** | Solo si se pasa filtro `modelo` (alternativa) |

#### **Campos NO Utilizados:**

- `cliente_id` - No se usa
- `cedula` - No se usa
- `nombres` - No se usa
- `total_financiamiento` - No se usa
- `fecha_requerimiento` - No se usa
- `modalidad_pago` - No se usa
- `numero_cuotas` - No se usa
- `cuota_periodo` - No se usa
- `tasa_interes` - No se usa
- `fecha_base_calculo` - No se usa
- `usuario_proponente` - No se usa
- `usuario_aprobador` - No se usa
- `fecha_registro` - No se usa
- `fecha_aprobacion` - No se usa
- Todos los demás campos - No se usan

---

## 📝 QUERY SQL EXACTA

### **Query Completa:**

```sql
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
```

### **Desglose de la Query:**

#### **1. SELECT - Campos Extraídos:**

```sql
EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año
```
- **Tabla:** `cuotas` (alias `c`)
- **Campo:** `fecha_vencimiento`
- **Operación:** Extrae el año de la fecha
- **Uso:** Para agrupar por año

```sql
EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes
```
- **Tabla:** `cuotas` (alias `c`)
- **Campo:** `fecha_vencimiento`
- **Operación:** Extrae el mes (1-12) de la fecha
- **Uso:** Para agrupar por mes

```sql
COALESCE(SUM(c.monto_cuota), 0) as morosidad
```
- **Tabla:** `cuotas` (alias `c`)
- **Campo:** `monto_cuota`
- **Operación:** Suma todos los montos de cuotas que cumplen las condiciones
- **Uso:** Este es el valor final de morosidad por mes

#### **2. FROM - Tablas Consultadas:**

```sql
FROM cuotas c
```
- **Tabla:** `cuotas`
- **Alias:** `c`
- **Razón:** Tabla principal donde están los datos de las cuotas

```sql
INNER JOIN prestamos p ON c.prestamo_id = p.id
```
- **Tabla:** `prestamos`
- **Alias:** `p`
- **Join:** `cuotas.prestamo_id = prestamos.id`
- **Razón:** Para acceder a los campos del préstamo (especialmente `estado`)

#### **3. WHERE - Condiciones:**

```sql
p.estado = 'APROBADO'
```
- **Tabla:** `prestamos`
- **Campo:** `estado`
- **Condición:** Solo préstamos aprobados
- **Razón:** No contar préstamos en borrador, rechazados, etc.

```sql
c.fecha_vencimiento >= :fecha_inicio
```
- **Tabla:** `cuotas`
- **Campo:** `fecha_vencimiento`
- **Condición:** Desde fecha inicio (ej: 2024-08-01)
- **Razón:** Limitar el rango de meses a mostrar

```sql
c.fecha_vencimiento < :fecha_fin_total
```
- **Tabla:** `cuotas`
- **Campo:** `fecha_vencimiento`
- **Condición:** Hasta hoy (sin incluir)
- **Razón:** Solo cuotas que ya vencieron, no futuras

```sql
c.estado != 'PAGADO'
```
- **Tabla:** `cuotas`
- **Campo:** `estado`
- **Condición:** Solo cuotas NO pagadas
- **Razón:** ⚠️ **CRÍTICO:** Si la cuota está pagada, no es morosidad

#### **4. GROUP BY - Agrupación:**

```sql
GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
```
- **Agrupa por:** Año y mes de `fecha_vencimiento`
- **Resultado:** Un registro por cada mes/año con la suma de morosidad

#### **5. ORDER BY - Ordenamiento:**

```sql
ORDER BY año, mes
```
- **Ordena por:** Año primero, luego mes
- **Resultado:** Datos ordenados cronológicamente

---

## 🔍 FLUJO DE DATOS DETALLADO

### **Paso 1: Acceso a la Base de Datos**

```
Base de Datos PostgreSQL
    └─> Tabla: cuotas
        ├─> Campo: prestamo_id
        ├─> Campo: fecha_vencimiento  ← SE USA
        ├─> Campo: monto_cuota         ← SE USA
        └─> Campo: estado              ← SE USA
    └─> Tabla: prestamos
        ├─> Campo: id
        ├─> Campo: estado              ← SE USA
        └─> Campos de filtros opcionales
```

### **Paso 2: Join de Tablas**

```sql
cuotas c  INNER JOIN  prestamos p
    ON c.prestamo_id = p.id
```

**Resultado:** Cada cuota tiene acceso a los datos de su préstamo

### **Paso 3: Aplicación de Filtros**

```sql
WHERE
    p.estado = 'APROBADO'                    ← Del préstamo
    AND c.fecha_vencimiento >= fecha_inicio   ← De la cuota
    AND c.fecha_vencimiento < hoy              ← De la cuota
    AND c.estado != 'PAGADO'                 ← De la cuota
```

**Resultado:** Solo cuotas que cumplen todas las condiciones

### **Paso 4: Extracción de Datos**

Para cada cuota que cumple:
- **Año:** `EXTRACT(YEAR FROM fecha_vencimiento)` → 2024
- **Mes:** `EXTRACT(MONTH FROM fecha_vencimiento)` → 8
- **Monto:** `monto_cuota` → 5000.00

### **Paso 5: Agrupación y Suma**

```
Agrupar por: (año, mes)
Sumar: monto_cuota

Ejemplo:
  (2024, 8) → Suma todas las cuotas de Agosto 2024
  (2024, 9) → Suma todas las cuotas de Septiembre 2024
```

### **Paso 6: Resultado Final**

```python
{
    (2024, 8): 65000.0,   # Suma de todas las cuotas de Agosto 2024
    (2024, 9): 72000.0,   # Suma de todas las cuotas de Septiembre 2024
    (2024, 10): 90000.0,  # Suma de todas las cuotas de Octubre 2024
    ...
}
```

---

## 📊 DIAGRAMA DE DATOS

```
┌─────────────────────────────────────────────────────────┐
│                    BASE DE DATOS                         │
└─────────────────────────────────────────────────────────┘
                          │
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│   TABLA: cuotas  │              │ TABLA: prestamos │
├──────────────────┤              ├──────────────────┤
│ id               │              │ id              │
│ prestamo_id ─────┼─── JOIN ─────┤ estado           │
│ fecha_vencimiento│              │ analista         │
│ monto_cuota      │              │ concesionario    │
│ estado           │              │ producto         │
│ ...              │              │ modelo_vehiculo  │
└──────────────────┘              └──────────────────┘
        │                                   │
        │                                   │
        └───────────────┬───────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   QUERY SQL           │
            │                       │
            │ SELECT                │
            │   año, mes            │
            │   SUM(monto_cuota)   │
            │                       │
            │ WHERE                 │
            │   estado != 'PAGADO'  │
            │   fecha_vencimiento   │
            │   prestamo.estado     │
            │                       │
            │ GROUP BY año, mes     │
            └───────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   RESULTADO            │
            │                       │
            │ Mes | Morosidad       │
            │ --------------------  │
            │ Ago 2024 | 65000      │
            │ Sep 2024 | 72000      │
            │ Oct 2024 | 90000      │
            │ ...                   │
            └───────────────────────┘
```

---

## ✅ RESUMEN DE FUENTES DE DATOS

### **Tablas Consultadas:**

1. ✅ **`cuotas`** (tabla principal)
   - Campo: `fecha_vencimiento` → Para filtrar y agrupar
   - Campo: `monto_cuota` → Para sumar
   - Campo: `estado` → Para filtrar (`!= 'PAGADO'`)
   - Campo: `prestamo_id` → Para hacer JOIN

2. ✅ **`prestamos`** (tabla secundaria, solo para filtros)
   - Campo: `id` → Para hacer JOIN
   - Campo: `estado` → Para filtrar (`= 'APROBADO'`)
   - Campos opcionales: `analista`, `concesionario`, `producto`, `modelo_vehiculo`

### **Tablas NO Consultadas:**

❌ `pagos_staging`
❌ `pagos`
❌ `cobros`
❌ `pago_cuotas`
❌ `clientes`
❌ Cualquier otra tabla

### **Campos Clave:**

| Campo | Tabla | Uso | Importancia |
|-------|-------|-----|-------------|
| `monto_cuota` | `cuotas` | Suma para calcular morosidad | ⭐⭐⭐ CRÍTICO |
| `estado` | `cuotas` | Filtro `!= 'PAGADO'` | ⭐⭐⭐ CRÍTICO |
| `fecha_vencimiento` | `cuotas` | Filtro y agrupación | ⭐⭐⭐ CRÍTICO |
| `estado` | `prestamos` | Filtro `= 'APROBADO'` | ⭐⭐ IMPORTANTE |
| `prestamo_id` | `cuotas` | JOIN con prestamos | ⭐ IMPORTANTE |

---

## 🎯 CONCLUSIÓN

**Los datos se toman EXCLUSIVAMENTE de:**

1. ✅ **Tabla `cuotas`:**
   - `monto_cuota` → Se suma
   - `fecha_vencimiento` → Se usa para filtrar y agrupar
   - `estado` → Se usa para filtrar (`!= 'PAGADO'`)

2. ✅ **Tabla `prestamos`:**
   - `estado` → Se usa para filtrar (`= 'APROBADO'`)
   - Campos opcionales para filtros adicionales

**NO se consultan:**
- ❌ Tablas de cobros
- ❌ Tablas de pagos realizados
- ❌ Tablas de registros de pago
- ❌ Cualquier otra tabla

**El cálculo es DIRECTO y SIMPLE:** Solo suma montos de cuotas no pagadas, agrupadas por mes de vencimiento.

---

**Documento generado automáticamente**
**Última actualización:** 2025-01-04

