# 📊 CORRESPONDENCIA: Columnas de la Imagen vs Base de Datos

## 🔍 Columnas de la Imagen

Según la imagen proporcionada, las columnas son:

| # | Columna Imagen | Descripción |
|---|----------------|-------------|
| 1 | `cedula` | Cédula de identidad del cliente |
| 2 | `TOTAL FINANCIAMIENTO` | Monto total del préstamo |
| 3 | `ABONOS` | Total de abonos pagados |

---

## 🗄️ Columnas Equivalentes en la Base de Datos

### ✅ Tabla: `prestamos`

| Columna Imagen | Columna BD | Tipo | Tabla | Descripción |
|----------------|------------|------|-------|-------------|
| `cedula` | `cedula` | VARCHAR(20) | `prestamos` | ✅ **Coincide exactamente** |
| `TOTAL FINANCIAMIENTO` | `total_financiamiento` | NUMERIC(15,2) | `prestamos` | ✅ Monto total del préstamo |

---

### ✅ Tabla: `cuotas` (Cálculo Agregado)

| Columna Imagen | Columna BD | Tipo | Tabla | Cálculo |
|----------------|------------|------|-------|---------|
| `ABONOS` | `SUM(total_pagado)` | NUMERIC(12,2) | `cuotas` | ✅ Suma de `cuotas.total_pagado` agrupada por `prestamos.cedula` |

**Query SQL para calcular ABONOS:**
```sql
SELECT 
    p.cedula,
    COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula IS NOT NULL
GROUP BY p.cedula;
```

---

### ✅ Tabla: `abono_2026` (Valores de Referencia)

| Columna Imagen | Columna BD | Tipo | Tabla | Descripción |
|----------------|------------|------|-------|-------------|
| `cedula` | `cedula` | VARCHAR(20) | `abono_2026` | ✅ Cédula del cliente |
| `ABONOS` | `abonos` | INTEGER | `abono_2026` | ✅ **Valor de referencia desde la imagen** (total_abonos_imagen) |

**Nota:** La columna `abonos` en `abono_2026` almacena los valores de referencia que vienen de la imagen.

---

## 📋 Resumen de Correspondencias

### Para la Columna `cedula`:
- ✅ `prestamos.cedula` → VARCHAR(20)
- ✅ `abono_2026.cedula` → VARCHAR(20)

### Para la Columna `TOTAL FINANCIAMIENTO`:
- ✅ `prestamos.total_financiamiento` → NUMERIC(15,2)

### Para la Columna `ABONOS`:
- ✅ **Desde BD:** `SUM(cuotas.total_pagado)` agrupado por `prestamos.cedula`
- ✅ **Desde Imagen:** `abono_2026.abonos` (valores de referencia)

---

## 🔄 Comparación: BD vs Imagen

### Query para Comparar:

```sql
WITH abonos_bd AS (
    SELECT 
        p.cedula,
        p.total_financiamiento,
        COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IS NOT NULL
    GROUP BY p.cedula, p.total_financiamiento
),
abonos_imagen AS (
    SELECT 
        cedula,
        COALESCE(abonos::numeric, 0) AS total_abonos_imagen
    FROM abono_2026
    WHERE cedula IS NOT NULL
)
SELECT 
    COALESCE(bd.cedula, img.cedula) AS cedula,
    bd.total_financiamiento,
    COALESCE(bd.total_abonos_bd, 0) AS total_abonos_bd,
    COALESCE(img.total_abonos_imagen, 0) AS total_abonos_imagen,
    ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(img.total_abonos_imagen, 0)) AS diferencia
FROM abonos_bd bd
FULL OUTER JOIN abonos_imagen img ON bd.cedula = img.cedula
ORDER BY diferencia DESC;
```

---

## 📝 Columnas Similares en Otras Tablas

### Tabla: `clientes`
- `cedula` → VARCHAR(20) - Cédula del cliente
- `nombres` → VARCHAR(100) - Nombre completo

### Tabla: `cuotas`
- `total_pagado` → NUMERIC(12,2) - Total pagado en esta cuota
- `capital_pagado` → NUMERIC(12,2) - Capital pagado
- `interes_pagado` → NUMERIC(12,2) - Interés pagado
- `monto_cuota` → NUMERIC(12,2) - Monto programado de la cuota

### Tabla: `pagos`
- `monto` → NUMERIC(12,2) - Monto del pago individual
- `activo` → BOOLEAN - Si el pago está activo

---

## 🎯 Uso en el Sistema

### En el Frontend (`/reportes`):
- **`total_abonos_bd`** → Calculado desde `SUM(cuotas.total_pagado)`
- **`total_abonos_imagen`** → Leído desde `abono_2026.abonos`
- **`diferencia`** → `ABS(total_abonos_bd - total_abonos_imagen)`

### En el Backend (`/api/v1/reportes/diferencias-abonos`):
- Compara `SUM(cuotas.total_pagado)` vs `abono_2026.abonos`
- Solo muestra préstamos con `requiere_revision = true` y diferencia > 0.01
