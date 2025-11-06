# ✅ Confirmación: `cuotas.total_pagado` - Suma Acumulativa

## 📋 Respuesta Directa

**`cuotas.total_pagado` es la SUMA ACUMULATIVA de todos los `pagos.monto_pagado` que se aplican a esa cuota.**

**NO es un registro individual**, sino un campo que se va **incrementando** cada vez que se aplica un pago.

---

## 🔍 Evidencia en el Código

### Función `_aplicar_monto_a_cuota()` (línea 1078)

```python
def _aplicar_monto_a_cuota(cuota, monto_aplicar, fecha_pago, fecha_hoy, db):
    # ...
    cuota.capital_pagado += capital_aplicar      # ✅ Se SUMA (tabla cuotas.capital_pagado)
    cuota.interes_pagado += interes_aplicar      # ✅ Se SUMA (tabla cuotas.interes_pagado)
    cuota.total_pagado += monto_aplicar          # ✅ Se SUMA (tabla cuotas.total_pagado - ACUMULATIVO)
    # ...
```

**Operador `+=`** indica que se **SUMA** al valor existente, no se reemplaza.

**Campos reales:**
- `cuotas.capital_pagado` - Se incrementa con cada pago
- `cuotas.interes_pagado` - Se incrementa con cada pago
- `cuotas.total_pagado` - Se incrementa con cada pago (suma acumulativa)

---

## 📊 Ejemplo Práctico

### Escenario: Cuota con Múltiples Pagos

**Cuota Inicial (tabla `cuotas`):**
```
cuotas.numero_cuota = 1
cuotas.monto_cuota = 500.00
cuotas.total_pagado = 0.00  ← Inicialmente 0
cuotas.capital_pagado = 0.00
cuotas.interes_pagado = 0.00
```

**Pago 1: $200.00 (tabla `pagos` - registro individual)**
```python
# Se crea registro en tabla pagos:
pagos.id = 1
pagos.monto_pagado = 200.00
pagos.prestamo_id = 3708
pagos.numero_cuota = 1

# Se actualiza tabla cuotas (campo acumulativo):
cuotas.total_pagado += 200.00
# Resultado: cuotas.total_pagado = 0.00 + 200.00 = 200.00
```

**Pago 2: $150.00 (tabla `pagos` - registro individual)**
```python
# Se crea registro en tabla pagos:
pagos.id = 2
pagos.monto_pagado = 150.00
pagos.prestamo_id = 3708
pagos.numero_cuota = 1

# Se actualiza tabla cuotas (campo acumulativo):
cuotas.total_pagado += 150.00
# Resultado: cuotas.total_pagado = 200.00 + 150.00 = 350.00
```

**Pago 3: $150.00 (tabla `pagos` - registro individual)**
```python
# Se crea registro en tabla pagos:
pagos.id = 3
pagos.monto_pagado = 150.00
pagos.prestamo_id = 3708
pagos.numero_cuota = 1

# Se actualiza tabla cuotas (campo acumulativo):
cuotas.total_pagado += 150.00
# Resultado: cuotas.total_pagado = 350.00 + 150.00 = 500.00
```

**Estado Final (tabla `cuotas`):**
```
cuotas.total_pagado = 500.00  ← SUMA de todos los pagos (200 + 150 + 150)
cuotas.monto_cuota = 500.00
cuotas.estado = "PAGADO"  ← Porque total_pagado >= monto_cuota
```

---

## 🔄 Flujo de Actualización

### Tabla `pagos` (Registros Individuales)

Cada pago se registra **individualmente** en la tabla `pagos`:

| `pagos.id` | `pagos.prestamo_id` | `pagos.numero_cuota` | `pagos.monto_pagado` | `pagos.fecha_pago` |
|------------|---------------------|----------------------|---------------------|-------------------|
| 1 | 3708 | 1 | 200.00 | 2025-11-15 |
| 2 | 3708 | 1 | 150.00 | 2025-11-20 |
| 3 | 3708 | 1 | 150.00 | 2025-11-25 |

**Total en tabla `pagos`: 3 registros individuales**
- Cada registro tiene su propio `pagos.monto_pagado`
- Cada registro es independiente

### Tabla `cuotas` (Campo Acumulativo)

El campo `cuotas.total_pagado` en la tabla `cuotas` se **actualiza acumulativamente**:

| `cuotas.prestamo_id` | `cuotas.numero_cuota` | `cuotas.monto_cuota` | `cuotas.total_pagado` | `cuotas.estado` |
|----------------------|----------------------|---------------------|----------------------|-----------------|
| 3708 | 1 | 500.00 | **500.00** | PAGADO |

**`cuotas.total_pagado = 500.00`** = Suma de todos los `pagos.monto_pagado` (200 + 150 + 150)

**Campos relacionados también acumulativos:**
- `cuotas.capital_pagado` - Suma acumulativa de capital pagado
- `cuotas.interes_pagado` - Suma acumulativa de interés pagado
- `cuotas.mora_pagada` - Suma acumulativa de mora pagada

---

## 📝 Código que Confirma el Comportamiento

### 1. Cálculo de Monto Faltante (línea 1214)

```python
monto_faltante = cuota.monto_cuota - cuota.total_pagado
# Equivale a:
# monto_faltante = cuotas.monto_cuota - cuotas.total_pagado
```

**Lógica:** Si `cuotas.total_pagado` fuera un registro individual, no se podría calcular el faltante restando del `cuotas.monto_cuota`. Esto confirma que es un valor acumulativo.

### 2. Verificación de Estado (línea 1022)

```python
if cuota.total_pagado >= cuota.monto_cuota:
    cuota.estado = "PAGADO"
# Equivale a:
# if cuotas.total_pagado >= cuotas.monto_cuota:
#     cuotas.estado = "PAGADO"
```

**Lógica:** Se compara el `cuotas.total_pagado` (acumulado) con el `cuotas.monto_cuota` para determinar si está completamente pagada.

---

## ✅ Confirmación Final (Con Nombres Reales de BD)

| Aspecto | `pagos.monto_pagado` | `cuotas.total_pagado` |
|---------|---------------------|----------------------|
| **Tabla** | `pagos` | `cuotas` |
| **Tipo Dato** | `numeric(12,2)` | `numeric(12,2)` |
| **Permite NULL** | NO | YES |
| **Valor Default** | - | - |
| **Posición en Tabla** | 6 | 14 |
| **Tipo** | Registro individual | Campo acumulativo |
| **Cantidad** | Múltiples registros (uno por pago) | Un solo campo por cuota |
| **Actualización** | Se crea un nuevo registro (INSERT) | Se incrementa (`+=`) (UPDATE) |
| **Ejemplo** | `pagos.monto_pagado = 200.00` (registro 1)<br>`pagos.monto_pagado = 150.00` (registro 2)<br>`pagos.monto_pagado = 150.00` (registro 3) | `cuotas.total_pagado = 500.00` (suma de todos) |

---

## 🎯 Conclusión

**`cuotas.total_pagado` es la SUMA de todos los `pagos.monto_pagado` que se aplican a esa cuota.**

- ✅ **NO es un registro individual**
- ✅ **SÍ es un campo acumulativo** que se incrementa con cada pago
- ✅ Se actualiza con el operador `+=` (suma)
- ✅ Representa el total pagado hasta el momento para esa cuota

**Relación entre tablas:**
- **Tabla `pagos`**: Almacena cada pago **individualmente** (múltiples registros)
  - Cada registro tiene: `pagos.id`, `pagos.monto_pagado`, `pagos.prestamo_id`, `pagos.numero_cuota`
- **Tabla `cuotas`**: Almacena la **suma acumulativa** de todos los pagos aplicados a esa cuota (un solo campo)
  - Campo: `cuotas.total_pagado` = suma de todos los `pagos.monto_pagado` relacionados
  - Campos relacionados: `cuotas.capital_pagado`, `cuotas.interes_pagado`, `cuotas.mora_pagada` (también acumulativos)

**Ejemplo:**
- 3 registros en `pagos` con `pagos.monto_pagado` = 200, 150, 150
- 1 registro en `cuotas` con `cuotas.total_pagado` = 500 (suma de 200 + 150 + 150)

