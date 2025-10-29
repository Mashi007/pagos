# 📖 ACLARACIÓN: Definición Correcta de LTV

## ❓ **¿QUÉ ES CORRECTO?**

En financiamiento vehicular:

### **Escenario Real:**
```
Precio del Vehículo:        $10,000 (Valor Total)
Anticipo del Cliente:       $3,000  (Pago Inicial)
────────────────────────────────────────────
Monto Financiado:           $7,000  (Lo que se presta)
```

### **LTV (Loan to Value) - Definición Bancaria:**
```
LTV = (Préstamo / Valor del Activo) × 100
LTV = ($7,000 / $10,000) × 100 = 70%
```

**Interpretación:** Se está prestando el 70% del valor del vehículo.

---

## 🎯 **LO QUE EL USUARIO ESTÁ PIDIENDO:**

1. **"Cambia enganche por anticipo"** ✅
   - Enganche → Anticipo
   - Es el dinero que el cliente paga INICIALMENTE

2. **"Valor de garantía es total financiamiento"** ❓
   - Aquí hay una confusión

### **Análisis:**

En el sistema actual:
- **`prestamo.total_financiamiento`** = $7,000 (monto del préstamo)
- **`enganche_pagado`** = $3,000 (anticipo)
- **`valor_garantia`** = ??? (no está claro)

**Confusión:**
- Si "valor_garantia" = `total_financiamiento`, sería $7,000
- Pero en términos bancarios, debería ser $10,000 (valor del vehículo)

---

## 💡 **POSIBLES INTERPRETACIONES:**

### **Opción A: Sistema Actual (Asumiendo que el préstamo ES el total)**
Si `total_financiamiento` ya es el valor total del vehículo:
```
Total Financiamiento:       $10,000 (todo el vehículo)
Anticipo:                   $3,000  (30%)
────────────────────────────────────────────
LTV = (Anticipo / Total) × 100 = 30%
```

### **Opción B: Sistema Bancario Tradicional**
```
Valor del Vehículo:        $10,000
Anticipo:                   $3,000
────────────────────────────────────────────
Monto Prestado:             $7,000
LTV = (Monto Prestado / Valor Vehículo) × 100 = 70%
```

---

## 🔍 **NECESITO CONFIRMAR:**

**Usuario, necesito aclarar:**

1. **¿Qué representa `total_financiamiento` en tu sistema?**
   - ¿Es el valor total del vehículo ($10,000)?
   - ¿O es el monto que se va a prestar ($7,000)?

2. **¿Qué significa "anticipo" en tu contexto?**
   - ¿Es el dinero que el cliente paga antes de recibir el vehículo?
   - ¿O es parte del financiamiento que no está incluido en el préstamo?

3. **¿El "valor de garantía" debe ser:**
   - El valor total del vehículo (Valor Comercial)?
   - El valor del préstamo otorgado?

---

## 📝 **PROPUESTA:**

Con la información actual, propongo:

### **En el formulario de evaluación:**

**Campo 1: "Anticipo Pagado (USD)"**
```typescript
anticipo_pagado: prestamo.total_financiamiento || 0
// Valor por defecto: $10,000 (todo el vehículo)
// Puede ser editado a, por ejemplo, $3,000
```

**Campo 2: "Valor del Vehículo (USD)"**
```typescript
valor_vehiculo: prestamo.total_financiamiento || 0
// Valor por defecto: $10,000 (valor total)
// Fijo = Total del vehículo
```

**Cálculo de LTV:**
```typescript
const enganche_pct = (anticipo_pagado / valor_vehiculo) * 100
const ltv = ((valor_vehiculo - anticipo_pagado) / valor_vehiculo) * 100
// LTV = (Préstamo / Valor del Vehículo) * 100
```

**Ejemplo:**
```
Valor del Vehículo: $10,000
Anticipo:           $3,000
Préstamo:           $7,000 ($10,000 - $3,000)

Enganche % = ($3,000 / $10,000) × 100 = 30%
LTV = ($7,000 / $10,000) × 100 = 70%
```

---

## ❓ **PREGUNTA PARA EL USUARIO:**

¿Este es el comportamiento que quieres?

```
Campo "Anticipo Pagado": Pre-llenar con el total del vehículo ($10,000)
                         Usuario puede cambiarlo (ej: $3,000)

Campo "Valor de Garantía": Pre-llenar con el total ($10,000)
                             Usuario puede cambiarlo (ej: $8,000 si es usado)

Cálculo LTV: ((Valor - Anticipo) / Valor) × 100
```

**¿Confirmas que esto es correcto?**

