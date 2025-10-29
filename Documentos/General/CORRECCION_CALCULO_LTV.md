# 🔧 CORRECCIÓN: Cálculo de LTV (Loan to Value)

## ❌ **PROBLEMA IDENTIFICADO**

### **Error en Frontend:**

**Antes (INCORRECTO):**
```typescript
// Línea 114: Cálculo INCORRECTO
const ltv = ((prestamo.total_financiamiento - formData.enganche_pagado) / formData.valor_garantia) * 100

// Resultado: LTV = ((10000 - 2500) / 5000) * 100 = 150% ❌
```

**Problemas:**
1. ❌ Usa `valor_garantia` que no existe en el backend
2. ❌ Resta el enganche en lugar de dividirlo
3. ❌ Fórmula incorrecta que da "Infinity%" cuando el denominador es 0

### **Error en Datos Enviados:**

**Antes (INCORRECTO):**
```typescript
const datosEvaluacion = {
    ratio_endeudamiento_calculo: ratios.ratioEndeudamiento,  // ❌ Ya calculado
    ratio_cobertura_calculo: ratios.ratioCobertura,           // ❌ Ya calculado
    enganche_garantias_calculo: ratios.ltv,                   // ❌ Ya calculado
    // ... datos ya procesados
}
```

**Problema:** El backend espera los **datos originales** para calcular todo, no datos ya procesados.

---

## ✅ **SOLUCIÓN APLICADA**

### **1. Corrección del Cálculo de LTV:**

**Ahora (CORRECTO):**
```typescript
// Línea 113-115: Cálculo CORRECTO
const ltv = prestamo.total_financiamiento > 0
  ? (formData.enganche_pagado / prestamo.total_financiamiento) * 100
  : 0

// Resultado: LTV = (2500 / 10000) * 100 = 25% ✅
```

### **2. Corrección de Datos Enviados:**

**Ahora (CORRECTO):**
```typescript
const datosEvaluacion = {
    ingresos_mensuales: formData.ingresos_mensuales,           // ✅ Datos originales
    gastos_fijos_mensuales: formData.gastos_fijos_mensuales,   // ✅ Datos originales
    cuota_mensual: prestamo.cuota_periodo || 0,                 // ✅ Dato del préstamo
    historial_crediticio: formData.historial_crediticio,       // ✅ Dato original
    anos_empleo: formData.anos_empleo,                         // ✅ Dato original
    tipo_empleo: formData.tipo_empleo,                          // ✅ Dato original
    enganche_pagado: formData.enganche_pagado,                 // ✅ Dato original
    monto_financiado: prestamo.total_financiamiento,           // ✅ Dato del préstamo
    red_flags: redFlags,
    verificado_usuario: true
}
```

---

## 📖 **DEFINICIÓN CORRECTA DE LTV**

Según el backend (`prestamo_evaluacion_service.py` líneas 182-200):

```python
def calcular_ltv(
    enganche_pagado: Decimal,
    monto_financiado: Decimal,
) -> Decimal:
    """
    TABLA 7: ENGANCHE Y GARANTÍAS (LTV - Loan to Value)

    Formula: (Enganche Pagado / Monto Financiado) * 100

    Mide el porcentaje de enganche sobre el financiamiento.

    Returns:
        Porcentaje LTV
    """
    if monto_financiado <= 0:
        return Decimal("0.00")

    ltv = (enganche_pagado / monto_financiado) * Decimal(100)
    return ltv
```

### **Fórmula:**
```
LTV = (Enganche Pagado / Monto Financiado) * 100
```

### **Ejemplo:**
```
Monto Financiado:  $10,000
Enganche Pagado:   $2,500

LTV = ($2,500 / $10,000) * 100 = 25%
```

---

## 🎯 **RESPUESTA A TU PREGUNTA**

### **"¿Es enganche o financiamiento?"**

**AMBOS** son necesarios para el cálculo:

1. **Enganche Pagado:** Es el dinero que el cliente paga como adelanto
2. **Monto Financiado:** Es el monto total del préstamo

**La fórmula es:**
```
LTV (%) = (Enganche Pagado / Monto Financiado) * 100
```

### **Interpretación:**
- **LTV = 25%** significa que el cliente pagó 25% de enganche sobre el total financiado
- **LTV alto (≥30%)** = Baja el riesgo (10 puntos)
- **LTV bajo (<5%)** = Alto riesgo (0 puntos)

---

## 🔍 **¿QUÉ ES EL CAMPO "VALOR DE GARANTÍA"?**

El campo `valor_garantia` que aparece en el formulario **NO se usa** en el cálculo del LTV en el backend actual.

### **Uso Actual:**
- Se muestra en el formulario
- Se almacena en el formulario
- **NO se envía al backend**
- **NO se usa en el cálculo de LTV**

### **Recomendación:**
Si quieres usar el valor de la garantía en el futuro, necesitarías:
1. Agregar el campo `valor_garantia` al modelo de evaluación
2. Implementar un cálculo adicional que considere el ratio de garantía

Por ahora, el sistema solo evalúa el **enganche** (dinero pagado por el cliente) sobre el **financiamiento** (monto del préstamo).

---

## 📊 **ESCALA DE PUNTUACIÓN POR LTV**

```python
if ltv >= 30%:   return 10 puntos  # Excelente enganche
if ltv >= 20%:   return 8 puntos   # Muy buen enganche
if ltv >= 15%:   return 6 puntos   # Enganche moderado
if ltv >= 10%:   return 4 puntos  # Enganche bajo
if ltv >= 5%:    return 2 puntos  # Enganche muy bajo
else:            return 0 puntos  # Sin enganche suficiente
```

---

## ✅ **VERIFICACIÓN**

Antes de esta corrección:
- ❌ LTV mostraba "Infinity%" cuando había 0 en valor_garantia
- ❌ Los datos enviados al backend eran incorrectos
- ❌ El backend no podía calcular correctamente los criterios

Después de esta corrección:
- ✅ LTV se calcula correctamente: `(enganche / monto_financiado) * 100`
- ✅ Se envían los datos originales al backend
- ✅ El backend calcula todos los criterios automáticamente
- ✅ Ya no aparece "Infinity%" en la interfaz

---

## 🔗 **ARCHIVOS MODIFICADOS**

1. `frontend/src/components/prestamos/EvaluacionRiesgoForm.tsx`:
   - Líneas 113-115: Corrección de cálculo de LTV
   - Líneas 150-162: Corrección de datos enviados al backend

