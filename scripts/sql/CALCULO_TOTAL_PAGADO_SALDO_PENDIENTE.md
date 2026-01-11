# 📊 CÁLCULO: Total Pagado y Saldo Pendiente

## 🎯 Respuesta Directa

**El total pagado se calcula sumando `cuotas.total_pagado` de todas las cuotas.**  
**El saldo pendiente se calcula como `total_financiamiento - total_pagado` o sumando los campos pendientes.**

---

## 📍 Ubicaciones en el Código

### 1. **Backend: Cálculo de Total Pagado**

#### A. Por Cédula (Total de Abonos)
**Archivo:** `backend/app/api/v1/endpoints/reportes.py`  
**Función:** `obtener_diferencias_abonos()` (línea ~1883)

```python
# Suma de total_pagado de todas las cuotas por cédula
total_abonos_bd_query = db.query(
    func.coalesce(func.sum(Cuota.total_pagado), Decimal("0.00"))
).filter(
    Cuota.prestamo_id == prestamo.id
)
total_abonos_bd = total_abonos_bd_query.scalar() or Decimal("0.00")
```

**SQL equivalente:**
```sql
SELECT COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd
FROM cuotas c
WHERE c.prestamo_id = [PRESTAMO_ID];
```

---

#### B. Total Pagado en Cuotas (KPIs)
**Archivo:** `backend/app/api/v1/endpoints/kpis.py`  
**Función:** `_calcular_kpis_amortizaciones()` (línea ~188)

```python
# Suma de capital_pagado + interes_pagado + mora_pagada
total_pagado_cuotas_query = db.query(
    func.sum(Cuota.capital_pagado + Cuota.interes_pagado + Cuota.mora_pagada)
).join(Prestamo, Cuota.prestamo_id == Prestamo.id)
total_pagado_cuotas = total_pagado_cuotas_query.scalar() or Decimal("0")
```

**SQL equivalente:**
```sql
SELECT COALESCE(SUM(c.capital_pagado + c.interes_pagado + c.mora_pagada), 0) AS total_pagado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id;
```

---

### 2. **Backend: Cálculo de Saldo Pendiente**

#### A. Saldo Pendiente por Préstamo
**Archivo:** `backend/app/api/v1/endpoints/prestamos.py`  
**Función:** `obtener_resumen_prestamos_cliente()` (línea ~779)

```python
# Suma de capital_pendiente + interes_pendiente + monto_mora
cuotas_agregadas = db.query(
    Cuota.prestamo_id,
    func.sum(Cuota.capital_pendiente + Cuota.interes_pendiente + Cuota.monto_mora).label("saldo_pendiente")
).filter(Cuota.prestamo_id.in_(prestamos_ids)).group_by(Cuota.prestamo_id).all()
```

**SQL equivalente:**
```sql
SELECT 
    prestamo_id,
    SUM(capital_pendiente + interes_pendiente + monto_mora) AS saldo_pendiente
FROM cuotas
WHERE prestamo_id IN ([PRESTAMOS_IDS])
GROUP BY prestamo_id;
```

---

#### B. Saldo Pendiente Global (KPIs)
**Archivo:** `backend/app/api/v1/endpoints/kpis.py`  
**Función:** `_calcular_kpis_amortizaciones()` (línea ~163)

```python
# Suma de saldos pendientes de cuotas no pagadas
saldo_pendiente_query = db.query(
    func.sum(Cuota.capital_pendiente + Cuota.interes_pendiente + Cuota.monto_mora)
).join(Prestamo, Cuota.prestamo_id == Prestamo.id).filter(
    Cuota.estado.in_(["PENDIENTE", "ATRASADO", "PARCIAL"])
)
saldo_pendiente = saldo_pendiente_query.scalar() or Decimal("0")
```

**SQL equivalente:**
```sql
SELECT COALESCE(SUM(c.capital_pendiente + c.interes_pendiente + c.monto_mora), 0) AS saldo_pendiente
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL');
```

---

#### C. Saldo Pendiente en Reporte de Cartera
**Archivo:** `backend/app/api/v1/endpoints/reportes.py`  
**Función:** `generar_reporte_cartera()` (línea ~164)

```python
# Capital pendiente: suma de capital_pendiente de cuotas no pagadas
capital_pendiente = db.query(
    func.sum(func.coalesce(Cuota.capital_pendiente, Decimal("0.00")))
).join(Prestamo, Cuota.prestamo_id == Prestamo.id).filter(
    Prestamo.estado == "APROBADO",
    Cuota.estado != "PAGADO"
).scalar() or Decimal("0")

# Intereses pendientes: suma de interes_pendiente de cuotas no pagadas
intereses_pendientes = db.query(
    func.sum(func.coalesce(Cuota.interes_pendiente, Decimal("0.00")))
).join(Prestamo, Cuota.prestamo_id == Prestamo.id).filter(
    Prestamo.estado == "APROBADO",
    Cuota.estado != "PAGADO"
).scalar() or Decimal("0")

# Mora total: suma de monto_mora de cuotas con mora
mora_total = db.query(
    func.sum(func.coalesce(Cuota.monto_mora, Decimal("0.00")))
).join(Prestamo, Cuota.prestamo_id == Prestamo.id).filter(
    Prestamo.estado == "APROBADO",
    Cuota.monto_mora > Decimal("0.00")
).scalar() or Decimal("0")

# Saldo pendiente total
saldo_pendiente = capital_pendiente + intereses_pendientes + mora_total
```

**SQL equivalente:**
```sql
-- Capital pendiente
SELECT COALESCE(SUM(c.capital_pendiente), 0) AS capital_pendiente
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO' AND c.estado != 'PAGADO';

-- Intereses pendientes
SELECT COALESCE(SUM(c.interes_pendiente), 0) AS intereses_pendientes
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO' AND c.estado != 'PAGADO';

-- Mora total
SELECT COALESCE(SUM(c.monto_mora), 0) AS mora_total
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO' AND c.monto_mora > 0;

-- Saldo pendiente total
SELECT 
    COALESCE(SUM(c.capital_pendiente), 0) +
    COALESCE(SUM(c.interes_pendiente), 0) +
    COALESCE(SUM(c.monto_mora), 0) AS saldo_pendiente_total
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO' AND c.estado != 'PAGADO';
```

---

## 🔄 Fórmulas de Cálculo

### **Total Pagado**
```sql
-- Opción 1: Usando total_pagado (recomendado)
SELECT SUM(c.total_pagado) AS total_pagado
FROM cuotas c
WHERE c.prestamo_id = [PRESTAMO_ID];

-- Opción 2: Sumando componentes pagados
SELECT SUM(c.capital_pagado + c.interes_pagado + c.mora_pagada) AS total_pagado
FROM cuotas c
WHERE c.prestamo_id = [PRESTAMO_ID];
```

### **Saldo Pendiente**
```sql
-- Opción 1: Usando campos pendientes (recomendado)
SELECT SUM(c.capital_pendiente + c.interes_pendiente + c.monto_mora) AS saldo_pendiente
FROM cuotas c
WHERE c.prestamo_id = [PRESTAMO_ID] AND c.estado != 'PAGADO';

-- Opción 2: Calculando desde total_financiamiento
SELECT 
    p.total_financiamiento - COALESCE(SUM(c.total_pagado), 0) AS saldo_pendiente
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.id = [PRESTAMO_ID]
GROUP BY p.id, p.total_financiamiento;

-- Opción 3: Por cuota individual
SELECT 
    c.monto_cuota - COALESCE(c.total_pagado, 0) AS saldo_pendiente_cuota
FROM cuotas c
WHERE c.prestamo_id = [PRESTAMO_ID];
```

---

## 📋 Resumen de Columnas Utilizadas

| Concepto | Columnas Sumadas | Tabla | Descripción |
|----------|------------------|-------|-------------|
| **Total Pagado** | `total_pagado` | `cuotas` | Suma acumulativa de todos los pagos aplicados |
| **Total Pagado (Detallado)** | `capital_pagado + interes_pagado + mora_pagada` | `cuotas` | Suma de componentes pagados |
| **Saldo Pendiente** | `capital_pendiente + interes_pendiente + monto_mora` | `cuotas` | Suma de componentes pendientes |
| **Saldo Deudor** | `total_financiamiento - SUM(total_pagado)` | `prestamos` + `cuotas` | Diferencia entre financiamiento y pagado |

---

## 🎯 Ejemplo Práctico

### Préstamo con 3 Cuotas

**Datos iniciales:**
- `total_financiamiento` = $3,000.00
- Cuota 1: `monto_cuota` = $1,000.00, `total_pagado` = $800.00
- Cuota 2: `monto_cuota` = $1,000.00, `total_pagado` = $1,000.00
- Cuota 3: `monto_cuota` = $1,000.00, `total_pagado` = $0.00

**Cálculo de Total Pagado:**
```sql
SELECT SUM(total_pagado) AS total_pagado
FROM cuotas
WHERE prestamo_id = [ID];
-- Resultado: $1,800.00 (800 + 1000 + 0)
```

**Cálculo de Saldo Pendiente:**
```sql
-- Opción 1: Desde campos pendientes
SELECT SUM(capital_pendiente + interes_pendiente + monto_mora) AS saldo_pendiente
FROM cuotas
WHERE prestamo_id = [ID] AND estado != 'PAGADO';
-- Resultado: $1,200.00 (200 pendiente cuota 1 + 1000 pendiente cuota 3)

-- Opción 2: Desde total_financiamiento
SELECT total_financiamiento - SUM(total_pagado) AS saldo_pendiente
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.id = [ID]
GROUP BY p.id, p.total_financiamiento;
-- Resultado: $1,200.00 (3000 - 1800)
```

---

## ✅ Conclusión

**Dónde se suman las cuotas:**

1. **Total Pagado:**
   - Se suma `cuotas.total_pagado` de todas las cuotas del préstamo
   - Ubicación principal: `backend/app/api/v1/endpoints/reportes.py` y `kpis.py`

2. **Saldo Pendiente:**
   - Se suma `capital_pendiente + interes_pendiente + monto_mora` de cuotas no pagadas
   - O se calcula como `total_financiamiento - total_pagado`
   - Ubicación principal: `backend/app/api/v1/endpoints/prestamos.py`, `kpis.py`, `reportes.py`

**Columna clave:** `cuotas.total_pagado` → Suma acumulativa de todos los pagos aplicados a cada cuota.
