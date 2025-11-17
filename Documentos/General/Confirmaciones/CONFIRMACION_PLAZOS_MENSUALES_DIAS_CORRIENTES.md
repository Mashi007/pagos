# ✅ CONFIRMACIÓN: Plazos Mensuales se Calculan con 30 Días Corrientes (NO Calendario)

## 📋 RESPUESTA DIRECTA

**SÍ, CONFIRMADO:** Los plazos mensuales se calculan usando **30 DÍAS CORRIENTES**, NO meses calendario.

---

## 🔍 VERIFICACIÓN TÉCNICA

### **1. Código del Servicio de Amortización**

**Archivo:** `backend/app/services/prestamo_amortizacion_service.py`

**Importaciones (Líneas 6-8):**
```python
from datetime import date, timedelta  # ✅ Usa timedelta (días), NO relativedelta (meses)
from decimal import Decimal
```

**Cálculo de Intervalo (Líneas 130-144):**
```python
def _calcular_intervalo_dias(modalidad_pago: str) -> int:
    """
    Calcula días entre cuotas según modalidad.

    Args:
        modalidad_pago: MENSUAL, QUINCENAL o SEMANAL

    Returns:
        Número de días entre cada cuota  # ✅ RETORNA DÍAS, NO MESES
    """
    intervalos = {
        "MENSUAL": 30,      # ✅ 30 DÍAS CORRIENTES
        "QUINCENAL": 15,    # ✅ 15 DÍAS CORRIENTES
        "SEMANAL": 7,       # ✅ 7 DÍAS CORRIENTES
    }

    return intervalos.get(modalidad_pago, 30)  # Default mensual: 30 días
```

**Cálculo de Fechas de Vencimiento (Líneas 48-61):**
```python
# Calcular intervalo entre cuotas según modalidad
intervalo_dias = _calcular_intervalo_dias(prestamo.modalidad_pago)  # ✅ MENSUAL = 30 días

# Generar cada cuota
for numero_cuota in range(1, prestamo.numero_cuotas + 1):
    # ✅ SUMA DÍAS CORRIENTES, NO MESES CALENDARIO
    fecha_vencimiento = fecha_base + timedelta(days=intervalo_dias * numero_cuota)
```

---

## 📊 DIFERENCIA CRÍTICA: Días Corrientes vs. Meses Calendario

### **Método Actual (Días Corrientes - 30 días):**
```python
# Usa: timedelta(days=30)
fecha_base + timedelta(days=30 * numero_cuota)
```

### **Método NO Usado (Meses Calendario):**
```python
# NO usa: relativedelta(months=1)
# from dateutil.relativedelta import relativedelta
# fecha_base + relativedelta(months=numero_cuota)  # ❌ NO SE USA ESTO
```

---

## 📅 EJEMPLOS PRÁCTICOS

### **Ejemplo 1: Inicio 15 de Enero**

**Con Días Corrientes (30 días - ACTUAL):**

| Cuota | Cálculo | Fecha de Vencimiento |
|-------|---------|---------------------|
| 1 | `15 Ene + (30 * 1)` | **14 Feb** ✅ |
| 2 | `15 Ene + (30 * 2) = 15 Ene + 60 días` | **16 Mar** ✅ |
| 3 | `15 Ene + (30 * 3) = 15 Ene + 90 días` | **15 Abr** ✅ |
| 4 | `15 Ene + (30 * 4) = 15 Ene + 120 días` | **15 May** ✅ |

**⚠️ Si fuera Meses Calendario (NO se usa):**

| Cuota | Cálculo | Fecha de Vencimiento |
|-------|---------|---------------------|
| 1 | `15 Ene + 1 mes` | **15 Feb** ❌ |
| 2 | `15 Ene + 2 meses` | **15 Mar** ❌ |
| 3 | `15 Ene + 3 meses` | **15 Abr** ❌ |
| 4 | `15 Ene + 4 meses` | **15 May** ❌ |

**Diferencia clave:** Con días corrientes, las fechas pueden variar según la cantidad de días que tiene cada mes (28/29/30/31).

---

### **Ejemplo 2: Inicio 31 de Enero**

**Con Días Corrientes (30 días - ACTUAL):**

| Cuota | Cálculo | Fecha de Vencimiento |
|-------|---------|---------------------|
| 1 | `31 Ene + 30 días` | **02 Mar** ✅ |
| 2 | `31 Ene + 60 días` | **02 Abr** ✅ |
| 3 | `31 Ene + 90 días` | **02 May** ✅ |

**⚠️ Si fuera Meses Calendario (NO se usa):**
- Sería problemático porque febrero no tiene día 31
- Python ajustaría a 28/29 Feb, o error

**Con días corrientes:** Simplemente suma 30 días, funciona correctamente.

---

### **Ejemplo 3: Inicio 15 de Diciembre**

**Con Días Corrientes (30 días - ACTUAL):**

| Cuota | Cálculo | Fecha de Vencimiento |
|-------|---------|---------------------|
| 1 | `15 Dic + 30 días` | **14 Ene** (año siguiente) ✅ |
| 2 | `15 Dic + 60 días` | **13 Feb** (año siguiente) ✅ |
| 3 | `15 Dic + 90 días` | **15 Mar** (año siguiente) ✅ |

**Cambios de año:** Se manejan automáticamente con `timedelta`.

---

## ✅ VERIFICACIÓN DEL CÓDIGO

### **Evidencia 1: No se Importa `relativedelta`**
```python
# ✅ Línea 7
from datetime import date, timedelta  # timedelta para días

# ❌ NO HAY:
# from dateutil.relativedelta import relativedelta  # Para meses calendario
```

### **Evidencia 2: Función Retorna Días, No Meses**
```python
# ✅ Línea 130
def _calcular_intervalo_dias(modalidad_pago: str) -> int:
    # Retorna: 30, 15, o 7 (días)
    return intervalos.get(modalidad_pago, 30)
```

### **Evidencia 3: Uso de `timedelta(days=...)`**
```python
# ✅ Línea 61
fecha_vencimiento = fecha_base + timedelta(days=intervalo_dias * numero_cuota)
#                            ^^^^^^^^   ^^^^
#                            Suma días  Días corrientes
```

---

## 🔄 COMPARACIÓN: Días Corrientes vs. Meses Calendario

| Aspecto | **Días Corrientes (ACTUAL)** | Meses Calendario (NO usado) |
|---------|------------------------------|------------------------------|
| **Función Python** | `timedelta(days=30)` | `relativedelta(months=1)` |
| **Intervalo Mensual** | 30 días fijos | 1 mes calendario |
| **Cuota 1 desde 15 Ene** | 14 Feb | 15 Feb |
| **Cuota 1 desde 31 Ene** | 02 Mar | 28/29 Feb |
| **Consistencia** | Siempre 30 días | Varía (28-31 días) |
| **Comportamiento** | Predecible | Depende del mes |

---

## 📋 TABLA DE INTERVALOS POR MODALIDAD

| Modalidad | Días Corrientes | Ejemplo de Cálculo |
|-----------|-----------------|-------------------|
| **MENSUAL** | **30 días** ✅ | `fecha_base + timedelta(days=30 * numero_cuota)` |
| **QUINCENAL** | **15 días** ✅ | `fecha_base + timedelta(days=15 * numero_cuota)` |
| **SEMANAL** | **7 días** ✅ | `fecha_base + timedelta(days=7 * numero_cuota)` |

---

## 🎯 CONFIRMACIÓN FINAL

### **✅ SÍ, CONFIRMADO:**

1. **Modalidad MENSUAL = 30 DÍAS CORRIENTES**
   - No usa meses calendario
   - No usa `relativedelta`
   - Usa `timedelta(days=30)`

2. **Cálculo de Fechas:**
   - Cuota 1: `fecha_base + 30 días`
   - Cuota 2: `fecha_base + 60 días`
   - Cuota 3: `fecha_base + 90 días`
   - etc.

3. **Ventajas del Método Actual:**
   - ✅ Predecible (siempre 30 días)
   - ✅ Maneja correctamente fechas como 31 de enero
   - ✅ Funciona con cualquier fecha base
   - ✅ No depende de la cantidad de días del mes

---

## 📝 NOTAS IMPORTANTES

### **Pregunta: ¿Por qué 30 días y no meses calendario?**

**Respuesta:**
- **Simplicidad:** 30 días es más predecible y fácil de calcular
- **Consistencia:** Todas las cuotas tienen exactamente el mismo intervalo
- **Manejo de fechas especiales:** Funciona bien con fechas como 31 de enero que no tienen equivalente el mes siguiente

### **Ejemplo Real:**

Si un préstamo inicia el **15 de enero de 2025**:
- **Cuota 1:** 15 Ene + 30 días = **14 de febrero de 2025** (NO 15 de febrero)
- **Cuota 2:** 15 Ene + 60 días = **16 de marzo de 2025** (NO 15 de marzo)
- **Cuota 3:** 15 Ene + 90 días = **15 de abril de 2025** (coincide por casualidad)

---

## ✅ CONCLUSIÓN

**Los plazos mensuales se calculan con 30 DÍAS CORRIENTES, NO con meses calendario.**

El sistema usa:
- ✅ `timedelta(days=30)` para intervalos mensuales
- ✅ Suma días corrientes desde la fecha base
- ✅ NO usa `relativedelta(months=1)` para meses calendario

**Esto es intencional y correcto para mantener consistencia en los intervalos de pago.**

