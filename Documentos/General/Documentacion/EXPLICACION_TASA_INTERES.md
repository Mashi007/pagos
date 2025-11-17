# 📊 Explicación: ¿De dónde toma la tasa de interés el sistema?

## 🎯 Respuesta Rápida

La tasa de interés viene de **la evaluación de riesgo** y se aplica al préstamo durante la **aprobación automática**.

---

## 📋 Flujo Completo

### 1️⃣ **Evaluación de Riesgo**
```python
# backend/app/services/prestamo_evaluacion_service.py (líneas 552-582)

condiciones = {
    "A": {
        "tasa_interes_aplicada": Decimal("15.0"),  # 15% anual
        "plazo_maximo": 36,
        ...
    },
    "B": {
        "tasa_interes_aplicada": Decimal("20.0"),  # 20% anual
        "plazo_maximo": 30,
        ...
    },
    "C": {
        "tasa_interes_aplicada": Decimal("24.0"),  # 24% anual
        "plazo_maximo": 24,
        ...
    },
    "D": {
        "tasa_interes_aplicada": Decimal("28.0"),  # 28% anual
        "plazo_maximo": 18,
        ...
    },
    "E": {
        "tasa_interes_aplicada": Decimal("30.0"),  # 30% anual
        "plazo_maximo": 12,
        ...
    },
}
```

**Depende de la clasificación de riesgo del cliente:**
- **Riesgo A** → 15% anual
- **Riesgo B** → 20% anual
- **Riesgo C** → 24% anual
- **Riesgo D** → 28% anual
- **Riesgo E** → 30% anual (NO aprobar)

---

### 2️⃣ **Aplicación en la Aprobación Automática**

```python
# backend/app/api/v1/endpoints/prestamos.py (líneas 785-802)

# La evaluación devuelve: evaluacion.tasa_interes_aplicada
condiciones = {
    "tasa_interes": float(evaluacion.tasa_interes_aplicada or 0),  # Ejemplo: 15.0
    ...
}

# Se aplica al préstamo
if condiciones.get("tasa_interes"):
    prestamo.tasa_interes = Decimal(str(condiciones["tasa_interes"]))  # prestamo.tasa_interes = 15.0
```

---

### 3️⃣ **Cálculo en la Tabla de Amortización**

```python
# backend/app/services/prestamo_amortizacion_service.py (líneas 51-56)

# Tasa de interés mensual (convertir anual a mensual)
if prestamo.tasa_interes == Decimal("0.00"):
    tasa_mensual = Decimal("0.00")
else:
    tasa_mensual = Decimal(prestamo.tasa_interes) / Decimal(100) / Decimal(12)
    # Ejemplo: 15% → 15/100/12 = 0.0125 (1.25% mensual)
```

---

### 4️⃣ **Cálculo de Interés por Cuota**

```python
# backend/app/services/prestamo_amortizacion_service.py (líneas 72-74)

monto_interes = saldo_capital * tasa_mensual
# Ejemplo: Si saldo = $466.19, tasa_mensual = 0.0125
# Interés = $466.19 × 0.0125 = $5.83

monto_capital = monto_cuota - monto_interes
# Ejemplo: $38.85 - $5.83 = $33.02 de capital
```

---

## 🔍 Ejemplo: Préstamo #9 (Juan García)

### Datos Originales
- Monto total: $466.19
- Cuotas: 12
- Cuota fija: $38.85

### ¿Qué clasificación de riesgo tiene Juan García?

**Respuesta: Debes verificar en la tabla `prestamos_evaluacion`:**
```sql
SELECT
    prestamo_id,
    clasificacion_riesgo,
    tasa_interes_aplicada,
    decision_final
FROM prestamos_evaluacion
WHERE prestamo_id = 9;
```

**Posibles resultados:**
- Si `clasificacion_riesgo = 'A'` → `tasa_interes_aplicada = 15.0%`
- Si `clasificacion_riesgo = 'B'` → `tasa_interes_aplicada = 20.0%`
- Si `clasificacion_riesgo = 'C'` → `tasa_interes_aplicada = 24.0%`
- Si `clasificacion_riesgo = 'D'` → `tasa_interes_aplicada = 28.0%`

---

## ❓ Verificación en Base de Datos

Ejecuta en **DBeaver**:

```sql
-- Ver qué tasa tiene actualmente el préstamo
SELECT
    id,
    tasa_interes,
    estado
FROM prestamos
WHERE id = 9;

-- Ver la clasificación de riesgo
SELECT
    prestamo_id,
    clasificacion_riesgo,
    tasa_interes_aplicada,
    puntuacion_total,
    decision_final
FROM prestamos_evaluacion
WHERE prestamo_id = 9;
```

---

## 🎯 Resumen

1. ✅ La tasa de interés viene de **la evaluación de riesgo**
2. ✅ Se basa en la **clasificación de riesgo** (A, B, C, D, E)
3. ✅ Se aplica **automáticamente** durante la aprobación
4. ✅ Se guarda en `prestamo.tasa_interes`
5. ✅ Se usa para calcular los **intereses de cada cuota**

---

## ⚠️ Problema Posible

Si ves en el frontend: **"Tasa de Interés: 1500.00%"**, hay un error de formato.

**Causa**: El valor se está multiplicando por 100 dos veces, o se está leyendo como decimal en lugar de porcentaje.

**Solución**: Verificar cómo se muestra en el frontend (componente PrestamoDetalleModal).

