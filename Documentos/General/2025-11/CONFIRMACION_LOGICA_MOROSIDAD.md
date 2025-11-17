# ✅ CONFIRMACIÓN: Lógica de Cálculo de Morosidad

## 📋 LÓGICA ESPECIFICADA POR EL USUARIO

1. **Sumar TODOS los pagos programados** (monto_cuota) que vencen en ese mes según amortización - de TODOS los créditos
2. **Restar TODOS los pagos** (monto_pagado) que corresponden a cuotas de ese mes - según fecha de registro
3. **Resultado**: Morosidad del mes = Programado - Pagado

---

## ✅ IMPLEMENTACIÓN ACTUAL

### 1. **PAGOS PROGRAMADOS** (Cuotas que vencen en el mes)

**Ubicación**: `dashboard.py:3545-3563`

```sql
SELECT
    EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
    COALESCE(SUM(c.monto_cuota), 0) as total_cuotas_programadas
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND EXTRACT(YEAR FROM c.fecha_vencimiento) >= 2024
GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
```

✅ **CORRECTO**: Suma todas las cuotas que vencen en cada mes según amortización.

---

### 2. **PAGOS REGISTRADOS** (Pagos registrados en ese mes por fecha_pago)

**Ubicación**: `dashboard.py:3663-3683` (sin filtros)

```sql
SELECT
    EXTRACT(YEAR FROM p.fecha_pago)::integer as año,
    EXTRACT(MONTH FROM p.fecha_pago)::integer as mes,
    COALESCE(SUM(p.monto_pagado), 0) as total_pagado
FROM pagos p
LEFT JOIN prestamos pr ON (
    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
)
WHERE p.monto_pagado IS NOT NULL
  AND p.monto_pagado > 0
  AND p.activo = TRUE
  AND pr.estado = 'APROBADO'
  AND EXTRACT(YEAR FROM p.fecha_pago) >= 2024
GROUP BY EXTRACT(YEAR FROM p.fecha_pago), EXTRACT(MONTH FROM p.fecha_pago)
```

✅ **CORRECTO**: Suma pagos registrados en cada mes por `fecha_pago`.

**Explicación**:
- Los pagos se cuentan por la fecha en que se registraron (`fecha_pago`), NO por la fecha de vencimiento de la cuota
- Si un pago se registra en marzo, cuenta para marzo
- La morosidad de febrero se eleva (no se pagó en febrero)
- La morosidad de marzo disminuye (se pagó en marzo)

---

### 3. **CÁLCULO DE MOROSIDAD**

**Ubicación**: `dashboard.py:3750`

```python
morosidad_mensual = max(0.0, float(monto_cuotas_programadas) - float(monto_pagado_mes))
```

✅ **CORRECTO**: `MAX(0, Programado - Pagado)`

---

## 🔍 VERIFICACIÓN DE LÓGICA

### Usan diferentes claves de tiempo (intencionalmente):

**Cuotas programadas**:
```python
cuotas_por_mes[(año_mes, num_mes)] = monto  # Clave: (año, mes) de fecha_vencimiento
```

**Pagos registrados**:
```python
pagos_por_mes[(año_mes, num_mes)] = monto  # Clave: (año, mes) de fecha_pago
```

✅ **DIFERENTES REFERENCIAS TEMPORALES** - Esto es correcto:
- Cuotas programadas: mes en que vencen (fecha_vencimiento)
- Pagos registrados: mes en que se registró el pago (fecha_pago)

**Esto permite detectar retrasos**: Si una cuota vence en febrero pero se paga en marzo, la morosidad de febrero aumenta y la de marzo disminuye.

---

## 📊 EJEMPLO PRÁCTICO

### Febrero 2025:

**Cuotas que vencen en febrero** (según amortización):
- Crédito A: Cuota #5 vence 15/02/2025, monto = $500
- Crédito B: Cuota #2 vence 20/02/2025, monto = $300
- **Total programado febrero**: $800

**Pagos registrados en febrero** (por fecha_pago):
- Pago registrado 10/02/2025: $300 (para cuota de enero)
- Pago registrado 25/02/2025: $200 (para cuota de febrero)
- **Total pagado en febrero**: $500

**Morosidad febrero**: `MAX(0, 800 - 500) = $300` ✅

### Marzo 2025:

**Cuotas que vencen en marzo**:
- Crédito A: Cuota #6 vence 15/03/2025, monto = $500
- Crédito B: Cuota #3 vence 20/03/2025, monto = $300
- **Total programado marzo**: $800

**Pagos registrados en marzo** (por fecha_pago):
- Pago registrado 05/03/2025: $600 (paga cuota de febrero que no se pagó a tiempo)
- Pago registrado 18/03/2025: $500 (paga cuota de marzo)
- **Total pagado en marzo**: $1,100

**Morosidad marzo**: `MAX(0, 800 - 1,100) = $0` ✅

**Nota**: El pago de $600 registrado en marzo paga la morosidad de febrero, por lo que:
- ✅ Morosidad de febrero se elevó (no se pagó a tiempo)
- ✅ Morosidad de marzo disminuyó (se pagó en marzo)

---

## ✅ CONCLUSIÓN

**La implementación es CORRECTA y coincide con la lógica especificada**:

1. ✅ Suma todas las cuotas programadas que vencen en el mes (según amortización) - por `fecha_vencimiento`
2. ✅ Resta todos los pagos registrados en ese mes (por fecha de registro) - por `fecha_pago`
3. ✅ Calcula morosidad = MAX(0, Programado - Pagado)

**Usan diferentes referencias temporales**:
- **Cuotas programadas**: agrupadas por mes de vencimiento (`fecha_vencimiento`)
- **Pagos registrados**: agrupados por mes de registro (`fecha_pago`)

**Esto permite detectar retrasos**:
- Si una cuota vence en febrero pero se paga en marzo:
  - ✅ Morosidad de febrero se eleva (no se pagó a tiempo)
  - ✅ Morosidad de marzo disminuye (se pagó en marzo)

---

## 🔧 CONFIRMACIÓN

La lógica implementada es correcta según tu descripción:

- ✅ Suma cuotas programadas por mes de vencimiento (fecha_vencimiento)
- ✅ Resta pagos registrados por mes de registro (fecha_pago)
- ✅ Calcula morosidad = MAX(0, Programado - Pagado)
- ✅ Si se registra en marzo, aplica a marzo (no a febrero)

