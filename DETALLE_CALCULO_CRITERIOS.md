# 📊 CALCULO DETALLADO DE CRITERIOS DE EVALUACIÓN

**Sistema de Puntuación: 0 a 100 puntos (6 criterios)**

---

## 🎯 RESUMEN DE PESOS

| # | Criterio | Peso | Puntos Máximos | Fórmula |
|---|---|---|---|---|
| 1 | Ratio de Endeudamiento | 25% | 25 pts | (Gastos + Cuota) / Ingresos |
| 2 | Ratio de Cobertura | 20% | 20 pts | Ingresos / Gastos |
| 3 | Historial Crediticio | 20% | 20 pts | Calificación cualitativa |
| 4 | Estabilidad Laboral | 15% | 15 pts | Años en el empleo |
| 5 | Tipo de Empleo | 10% | 10 pts | Tipo de contrato |
| 6 | Enganche y Garantías | 10% | 10 pts | % Enganche sobre financiamiento |
| **TOTAL** | | **100%** | **100 pts** | |

---

## 1️⃣ RATIO DE ENDEUDAMIENTO (25 puntos)

### 📐 **Fórmula:**

```
Ratio = (Gastos Fijos Mensuales + Cuota Mensual) / Ingresos Mensuales
```

### 📊 **Escala de Puntuación:**

```29:66:backend/app/services/prestamo_evaluacion_service.py
def calcular_ratio_endeudamiento(
    ingresos_mensuales: Decimal,
    gastos_fijos_mensuales: Decimal,
    cuota_mensual: Decimal,
) -> Decimal:
    """
    TABLA 2: RATIO DE ENDEUDAMIENTO

    Formula: (Gastos Fijos + Cuota Mensual) / Ingresos Mensuales

    Retorna:
        - Decimal con el valor del ratio (ej: 0.45 = 45%)
    """
    if ingresos_mensuales <= 0:
        return Decimal("999.99")  # Indicador de error

    ratio = (gastos_fijos_mensuales + cuota_mensual) / ingresos_mensuales
    return ratio


def evaluar_ratio_endeudamiento_puntos(ratio: Decimal) -> Decimal:
    """
    Evalúa puntos según ratio de endeudamiento.
    Rango óptimo: 0% - 30%

    Returns:
        Puntos de 0 a 25
    """
    if ratio <= Decimal("0.30"):  # 30% o menos
        return Decimal(25)
    elif ratio <= Decimal("0.40"):  # 31-40%
        return Decimal(20)
    elif ratio <= Decimal("0.50"):  # 41-50%
        return Decimal(15)
    elif ratio <= Decimal("0.60"):  # 51-60%
        return Decimal(10)
    else:  # Más de 60%
        return Decimal(5)
```

| Ratio (%) | Puntos | Interpretación |
|---|---|---|
| ≤ 30% | **25** | 🟢 Endeudamiento muy bajo, excelente |
| 31-40% | **20** | 🟢 Endeudamiento bajo |
| 41-50% | **15** | 🟡 Endeudamiento moderado |
| 51-60% | **10** | 🟠 Endeudamiento alto |
| > 60% | **5** | 🔴 Endeudamiento muy alto |

### 💡 **Ejemplos:**

#### **Ejemplo 1: Buen Ratio (25 puntos)**
```
Ingresos:     $1,500/mes
Gastos:       $300/mes
Cuota:        $150/mes

Ratio = ($300 + $150) / $1,500 = $450 / $1,500 = 0.30 (30%)
Puntos: 25 ✅
```

#### **Ejemplo 2: Ratio Moderado (15 puntos)**
```
Ingresos:     $2,000/mes
Gastos:       $700/mes
Cuota:        $350/mes

Ratio = ($700 + $350) / $2,000 = $1,050 / $2,000 = 0.525 (52.5%)
Puntos: 15 ⚠️
```

#### **Ejemplo 3: Ratio Alto (5 puntos)**
```
Ingresos:     $1,000/mes
Gastos:       $500/mes
Cuota:        $200/mes

Ratio = ($500 + $200) / $1,000 = $700 / $1,000 = 0.70 (70%)
Puntos: 5 ❌
```

---

## 2️⃣ RATIO DE COBERTURA (20 puntos)

### 📐 **Fórmula:**

```
Ratio = Ingresos Mensuales / Gastos Fijos Mensuales
```

### 📊 **Escala de Puntuación:**

```69:107:backend/app/services/prestamo_evaluacion_service.py
def calcular_ratio_cobertura(
    ingresos_mensuales: Decimal,
    gastos_fijos_mensuales: Decimal,
) -> Decimal:
    """
    TABLA 3: RATIO DE COBERTURA

    Formula: Ingresos Mensuales / Gastos Fijos Mensuales

    Mide cuántas veces los ingresos cubren los gastos.
    Ratio > 1.5 es saludable.

    Returns:
        Decimal con el ratio
    """
    if gastos_fijos_mensuales <= 0:
        return Decimal("999.99")

    ratio = ingresos_mensuales / gastos_fijos_mensuales
    return ratio


def evaluar_ratio_cobertura_puntos(ratio: Decimal) -> Decimal:
    """
    Evalúa puntos según ratio de cobertura.

    Returns:
        Puntos de 0 a 20
    """
    if ratio >= Decimal("2.0"):  # 2.0 o más
        return Decimal(20)
    elif ratio >= Decimal("1.5"):  # 1.5-1.99
        return Decimal(17)
    elif ratio >= Decimal("1.2"):  # 1.2-1.49
        return Decimal(12)
    elif ratio >= Decimal("1.0"):  # 1.0-1.19
        return Decimal(8)
    else:  # Menos de 1.0
        return Decimal(3)
```

| Ratio | Puntos | Interpretación |
|---|---|---|
| ≥ 2.0x | **20** | 🟢 Ingresos cubren 2x gastos |
| 1.5-1.99x | **17** | 🟢 Ingresos cubren 1.5x gastos |
| 1.2-1.49x | **12** | 🟡 Ingresos cubren 1.2x gastos |
| 1.0-1.19x | **8** | 🟠 Ingresos apenas cubren gastos |
| < 1.0x | **3** | 🔴 Ingresos no cubren gastos |

### 💡 **Ejemplos:**

#### **Ejemplo 1: Excelente Cobertura (20 puntos)**
```
Ingresos:     $3,000/mes
Gastos:       $1,200/mes

Ratio = $3,000 / $1,200 = 2.5x
Puntos: 20 ✅
```

#### **Ejemplo 2: Cobertura Buena (17 puntos)**
```
Ingresos:     $2,500/mes
Gastos:       $1,500/mes

Ratio = $2,500 / $1,500 = 1.67x
Puntos: 17 ✅
```

#### **Ejemplo 3: Cobertura Ajustada (8 puntos)**
```
Ingresos:     $1,800/mes
Gastos:       $1,500/mes

Ratio = $1,800 / $1,500 = 1.2x
Puntos: 8 ⚠️
```

#### **Ejemplo 4: Cobertura Insuficiente (3 puntos)**
```
Ingresos:     $800/mes
Gastos:       $1,000/mes

Ratio = $800 / $1,000 = 0.8x
Puntos: 3 ❌
```

---

## 3️⃣ HISTORIAL CREDITICIO (20 puntos)

### 📐 **Evaluación:**

```
Es un criterio cualitativo, no matemático
```

### 📊 **Escala de Puntuación:**

```110:129:backend/app/services/prestamo_evaluacion_service.py
def evaluar_historial_crediticio(calificacion: str) -> Dict[str, Decimal]:
    """
    Evalúa historial crediticio basado en calificación.

    Args:
        calificacion: "EXCELENTE", "BUENO", "REGULAR", "MALO"

    Returns:
        Dict con puntos y descripción
    """
    evaluaciones = {
        "EXCELENTE": {"puntos": Decimal(20), "descripcion": "Sin atrasos en 2+ años"},
        "BUENO": {"puntos": Decimal(15), "descripcion": "Algunos atrasos menores"},
        "REGULAR": {"puntos": Decimal(8), "descripcion": "Atrasos significativos"},
        "MALO": {"puntos": Decimal(2), "descripcion": "Múltiples incumplimientos"},
    }

    return evaluaciones.get(
        calificacion.upper(), {"puntos": Decimal(0), "descripcion": "Desconocido"}
    )
```

| Calificación | Puntos | Descripción |
|---|---|---|
| EXCELENTE | **20** | Sin atrasos en 2+ años |
| BUENO | **15** | Algunos atrasos menores |
| REGULAR | **8** | Atrasos significativos |
| MALO | **2** | Múltiples incumplimientos |

### 💡 **Ejemplos:**

#### **Ejemplo 1: Historial Excelente (20 puntos)**
```
Cliente ha pagado todos sus préstamos a tiempo en los últimos 2 años
Puntos: 20 ✅
```

#### **Ejemplo 2: Historial Regular (8 puntos)**
```
Cliente tiene 2-3 atrasos menores en el último año
Puntos: 8 ⚠️
```

---

## 4️⃣ ESTABILIDAD LABORAL (15 puntos)

### 📐 **Fórmula:**

```
Puntos = f(Años de Empleo)
```

### 📊 **Escala de Puntuación:**

```132:148:backend/app/services/prestamo_evaluacion_service.py
def evaluar_estabilidad_laboral(anos_empleo: Decimal) -> Decimal:
    """
    Evalúa estabilidad laboral según años en el trabajo.

    Returns:
        Puntos de 0 a 15
    """
    if anos_empleo >= Decimal(5):
        return Decimal(15)
    elif anos_empleo >= Decimal(3):
        return Decimal(12)
    elif anos_empleo >= Decimal(1):
        return Decimal(8)
    elif anos_empleo >= Decimal(0.5):  # 6 meses
        return Decimal(5)
    else:
        return Decimal(2)
```

| Años de Empleo | Puntos | Interpretación |
|---|---|---|
| ≥ 5 años | **15** | 🟢 Excelente estabilidad |
| 3-4.9 años | **12** | 🟢 Muy buena estabilidad |
| 1-2.9 años | **8** | 🟡 Estabilidad moderada |
| 0.5-0.9 años (6-11 meses) | **5** | 🟠 Estabilidad baja |
| < 0.5 años (< 6 meses) | **2** | 🔴 Estabilidad muy baja |

### 💡 **Ejemplos:**

#### **Ejemplo 1: Excelente Estabilidad (15 puntos)**
```
Años en el empleo: 7 años
Puntos: 15 ✅
```

#### **Ejemplo 2: Muy Buena Estabilidad (12 puntos)**
```
Años en el empleo: 3.5 años
Puntos: 12 ✅
```

#### **Ejemplo 3: Estabilidad Moderada (8 puntos)**
```
Años en el empleo: 1.8 años
Puntos: 8 🟡
```

#### **Ejemplo 4: Estabilidad Baja (5 puntos)**
```
Años en el empleo: 8 meses (0.67 años)
Puntos: 5 ⚠️
```

#### **Ejemplo 5: Estabilidad Muy Baja (2 puntos)**
```
Años en el empleo: 3 meses (0.25 años)
Puntos: 2 ❌
```

---

## 5️⃣ TIPO DE EMPLEO (10 puntos)

### 📐 **Evaluación:**

```
Puntos = f(Tipo de Empleo)
```

### 📊 **Escala de Puntuación:**

```151:179:backend/app/services/prestamo_evaluacion_service.py
def evaluar_tipo_empleo(tipo: str) -> Dict[str, Decimal]:
    """
    Evalúa tipo de empleo.

    Args:
        tipo: "FORMAL", "INDEPENDIENTE", "CONTRATADO", "TEMPORAL"

    Returns:
        Dict con puntos y descripción
    """
    evaluaciones = {
        "FORMAL": {
            "puntos": Decimal(10),
            "descripcion": "Empleo formal con beneficios",
        },
        "INDEPENDIENTE": {
            "puntos": Decimal(7),
            "descripcion": "Trabajador independiente estable",
        },
        "CONTRATADO": {
            "puntos": Decimal(6),
            "descripcion": "Contratado por tiempo determinado",
        },
        "TEMPORAL": {"puntos": Decimal(3), "descripcion": "Empleo temporal o eventual"},
    }

    return evaluaciones.get(
        tipo.upper(), {"puntos": Decimal(0), "descripcion": "Desconocido"}
    )
```

| Tipo de Empleo | Puntos | Descripción |
|---|---|---|
| FORMAL | **10** | Empleo formal con beneficios |
| INDEPENDIENTE | **7** | Trabajador independiente estable |
| CONTRATADO | **6** | Contratado por tiempo determinado |
| TEMPORAL | **3** | Empleo temporal o eventual |

### 💡 **Ejemplos:**

#### **Ejemplo 1: Empleo Formal (10 puntos)**
```
Tipo: FORMAL
Descripción: Empleado con planilla, beneficios sociales
Puntos: 10 ✅
```

#### **Ejemplo 2: Independiente Estable (7 puntos)**
```
Tipo: INDEPENDIENTE
Descripción: Profesional independiente con ingresos constantes
Puntos: 7 ✅
```

#### **Ejemplo 3: Empleo Temporal (3 puntos)**
```
Tipo: TEMPORAL
Descripción: Trabajo eventual, sin estabilidad
Puntos: 3 ⚠️
```

---

## 6️⃣ ENGANCHE Y GARANTÍAS (10 puntos)

### 📐 **Fórmula:**

```
LTV = (Enganche Pagado / Monto Financiado) * 100
```

### 📊 **Escala de Puntuación:**

```182:221:backend/app/services/prestamo_evaluacion_service.py
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


def evaluar_enganche_garantias(ltv: Decimal) -> Decimal:
    """
    Evalúa enganche y garantías según LTV.

    Returns:
        Puntos de 0 a 10
    """
    if ltv >= Decimal(30):  # 30% o más de enganche
        return Decimal(10)
    elif ltv >= Decimal(20):  # 20-29%
        return Decimal(8)
    elif ltv >= Decimal(15):  # 15-19%
        return Decimal(6)
    elif ltv >= Decimal(10):  # 10-14%
        return Decimal(4)
    elif ltv >= Decimal(5):  # 5-9%
        return Decimal(2)
    else:  # Menos de 5%
        return Decimal(0)
```

| % Enganche (LTV) | Puntos | Interpretación |
|---|---|---|
| ≥ 30% | **10** | 🟢 Excelente enganche |
| 20-29% | **8** | 🟢 Muy buen enganche |
| 15-19% | **6** | 🟡 Enganche moderado |
| 10-14% | **4** | 🟠 Enganche bajo |
| 5-9% | **2** | 🔴 Enganche muy bajo |
| < 5% | **0** | 🔴 Sin enganche suficiente |

### 💡 **Ejemplos:**

#### **Ejemplo 1: Excelente Enganche (10 puntos)**
```
Monto Financiado:  $10,000
Enganche Pagado:   $4,000

LTV = ($4,000 / $10,000) * 100 = 40%
Puntos: 10 ✅
```

#### **Ejemplo 2: Muy Buen Enganche (8 puntos)**
```
Monto Financiado:  $8,000
Enganche Pagado:   $2,000

LTV = ($2,000 / $8,000) * 100 = 25%
Puntos: 8 ✅
```

#### **Ejemplo 3: Enganche Moderado (6 puntos)**
```
Monto Financiado:  $12,000
Enganche Pagado:   $2,000

LTV = ($2,000 / $12,000) * 100 = 16.67%
Puntos: 6 🟡
```

#### **Ejemplo 4: Enganche Bajo (2 puntos)**
```
Monto Financiado:  $15,000
Enganche Pagado:   $500

LTV = ($500 / $15,000) * 100 = 3.33%
Puntos: 2 ❌
```

---

## 🎯 EJEMPLO COMPLETO DE CALCULO

### **Datos del Solicitante:**

```
Ingresos Mensuales:         $2,000
Gastos Fijos Mensuales:     $600
Cuota Mensual del Préstamo: $350
Historial Crediticio:       "BUENO"
Años en el Empleo:          2 años
Tipo de Empleo:             "FORMAL"
Monto Financiado:           $10,000
Enganche Pagado:            $2,500
```

### **Cálculo por Criterio:**

#### **1. Ratio de Endeudamiento:**
```
Ratio = ($600 + $350) / $2,000 = $950 / $2,000 = 0.475 (47.5%)
Puntos: 15 (rango 41-50%)
```

#### **2. Ratio de Cobertura:**
```
Ratio = $2,000 / $600 = 3.33x
Puntos: 20 (ratio ≥ 2.0x)
```

#### **3. Historial Crediticio:**
```
Calificación: "BUENO"
Puntos: 15
```

#### **4. Estabilidad Laboral:**
```
Años: 2
Puntos: 8 (rango 1-2.9 años)
```

#### **5. Tipo de Empleo:**
```
Tipo: "FORMAL"
Puntos: 10
```

#### **6. Enganche y Garantías:**
```
LTV = ($2,500 / $10,000) * 100 = 25%
Puntos: 8 (rango 20-29%)
```

### **📊 Puntuación Total:**

```
Total = 15 + 20 + 15 + 8 + 10 + 8 = 76 puntos
```

### **🎯 Clasificación y Decisión:**

```python
Puntuación: 76/100
Clasificación: MODERADO (60-79 puntos)
Decisión: CONDICIONAL
```

### **📋 Condiciones Aplicadas:**

```python
"MODERADO": {
    "tasa_interes_aplicada": 12.0%,
    "plazo_maximo": 30 meses,
    "enganche_minimo": 20.0%,
    "requisitos_adicionales": "Garante opcional"
}
```

---

## 📝 RESUMEN DE FÓRMULAS

```python
# 1. Ratio de Endeudamiento
points_1 = evaluar_ratio_endeudamiento_puntos(
    (gastos + cuota) / ingresos
)

# 2. Ratio de Cobertura
points_2 = evaluar_ratio_cobertura_puntos(
    ingresos / gastos
)

# 3. Historial Crediticio
points_3 = evaluar_historial_crediticio(calificacion)["puntos"]

# 4. Estabilidad Laboral
points_4 = evaluar_estabilidad_laboral(anos_empleo)

# 5. Tipo de Empleo
points_5 = evaluar_tipo_empleo(tipo_empleo)["puntos"]

# 6. Enganche
points_6 = evaluar_enganche_garantias(
    (enganche / monto_financiado) * 100
)

# TOTAL
total_score = points_1 + points_2 + points_3 + points_4 + points_5 + points_6
```

---

## 🔗 REFERENCIA DEL CÓDIGO

Ver implementación completa en:
- `backend/app/services/prestamo_evaluacion_service.py` (líneas 29-443)

