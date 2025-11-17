# 📊 Cálculo Detallado de Riesgo ML Impago

**Fecha:** 2025-01-17  
**Objetivo:** Explicar cómo se calcula el riesgo ML Impago y cómo ver el detalle para clientes específicos

---

## 🔍 Criterios de Clasificación

El modelo ML clasifica el riesgo en tres niveles basándose en la **probabilidad de impago**:

| Probabilidad de Impago | Nivel de Riesgo | Criterio |
|------------------------|-----------------|----------|
| **≥ 70%** (0.7 o más) | **Alto** | `probabilidad_impago >= 0.7` |
| **40% - 69.9%** (0.4 a 0.699) | **Medio** | `0.4 <= probabilidad_impago < 0.7` |
| **< 40%** (menos de 0.4) | **Bajo** | `probabilidad_impago < 0.4` |

---

## 📋 Features Utilizadas (12 Features)

El modelo analiza las siguientes características del historial de pagos:

1. **`porcentaje_cuotas_pagadas`**: Porcentaje de cuotas pagadas sobre el total
2. **`promedio_dias_mora`**: Promedio de días de mora en todas las cuotas
3. **`numero_cuotas_atrasadas`**: Cantidad de cuotas en estado "ATRASADO"
4. **`numero_cuotas_parciales`**: Cantidad de cuotas pagadas parcialmente
5. **`tasa_cumplimiento`**: Porcentaje de cuotas vencidas que fueron pagadas a tiempo
6. **`dias_desde_ultimo_pago`**: Días transcurridos desde el último pago realizado
7. **`numero_cuotas_restantes`**: Cuotas pendientes o futuras
8. **`monto_promedio_cuota`**: Monto promedio de cada cuota
9. **`ratio_monto_pendiente`**: Porcentaje del monto total que aún está pendiente
10. **`tendencia_pagos`**: -1 (empeora), 0 (estable), 1 (mejora)
11. **`cuotas_vencidas_sin_pagar`**: Cantidad de cuotas vencidas que no han sido pagadas
12. **`monto_total_pendiente`**: Monto total que falta por pagar

---

## 🔧 Cómo Ver el Cálculo Detallado

### Endpoint: `/api/v1/ai/training/ml-impago/calcular-detalle/{prestamo_id}`

Este endpoint muestra el cálculo completo para un préstamo específico.

**Ejemplo de uso:**
```
GET /api/v1/ai/training/ml-impago/calcular-detalle/123
```

**Respuesta incluye:**
- Información del préstamo (cédula, nombres)
- Modelo ML usado
- Estadísticas de cuotas (total, pagadas, atrasadas, etc.)
- Estadísticas financieras (montos pagados, pendientes)
- **Todas las 12 features extraídas con sus valores**
- Probabilidad de impago calculada
- Nivel de riesgo asignado
- **Criterio de clasificación** (explicación de por qué es Alto/Medio/Bajo)
- Umbrales de clasificación

---

## 📊 Ejemplo de Respuesta

```json
{
  "prestamo_id": 123,
  "cedula": "V27076582",
  "nombres": "FERNANDO ARTURO GARCIA ABACHE",
  "modelo_usado": {
    "id": 1,
    "nombre": "Modelo Impago Cuotas 20251117_015506",
    "algoritmo": "random_forest",
    "accuracy": 1.0
  },
  "fecha_calculo": "2025-01-17",
  "estadisticas_cuotas": {
    "total_cuotas": 36,
    "cuotas_pagadas": 0,
    "cuotas_atrasadas": 36,
    "cuotas_parciales": 0,
    "cuotas_pendientes": 0,
    "cuotas_vencidas": 36,
    "cuotas_vencidas_sin_pagar": 36
  },
  "estadisticas_financieras": {
    "monto_total_prestamo": 1440.0,
    "monto_total_pagado": 0.0,
    "monto_total_pendiente": 1440.0,
    "porcentaje_pagado": 0.0
  },
  "features_extraidas": {
    "porcentaje_cuotas_pagadas": 0.0,
    "promedio_dias_mora": 15.5,
    "numero_cuotas_atrasadas": 36.0,
    "numero_cuotas_parciales": 0.0,
    "tasa_cumplimiento": 0.0,
    "dias_desde_ultimo_pago": 120.0,
    "numero_cuotas_restantes": 0.0,
    "monto_promedio_cuota": 40.0,
    "ratio_monto_pendiente": 100.0,
    "tendencia_pagos": -1.0,
    "cuotas_vencidas_sin_pagar": 36.0,
    "monto_total_pendiente": 1440.0
  },
  "prediccion": {
    "probabilidad_impago": 1.0,
    "probabilidad_impago_porcentaje": 100.0,
    "probabilidad_pago": 0.0,
    "prediccion": "No pagará",
    "nivel_riesgo": "Alto",
    "confidence": 1.0,
    "recomendacion": "Alta probabilidad de impago. Considerar acciones preventivas."
  },
  "criterio_clasificacion": "probabilidad_impago >= 0.7 (1.000 >= 0.7) → Riesgo ALTO",
  "umbrales": {
    "alto": "probabilidad_impago >= 0.7 (70% o más)",
    "medio": "0.4 <= probabilidad_impago < 0.7 (40% a 69.9%)",
    "bajo": "probabilidad_impago < 0.4 (menos de 40%)"
  }
}
```

---

## 🔍 Interpretación del Ejemplo

Para el cliente con **100.0% de probabilidad de impago**:

### Features que indican alto riesgo:
- ✅ `porcentaje_cuotas_pagadas: 0.0%` - No ha pagado ninguna cuota
- ✅ `cuotas_vencidas_sin_pagar: 36` - Todas las cuotas están vencidas sin pagar
- ✅ `tasa_cumplimiento: 0.0%` - No ha cumplido con ninguna cuota vencida
- ✅ `dias_desde_ultimo_pago: 120` - Hace 120 días desde el último pago
- ✅ `tendencia_pagos: -1.0` - La tendencia es negativa (empeora)
- ✅ `ratio_monto_pendiente: 100.0%` - Todo el monto está pendiente

### Criterio aplicado:
```
probabilidad_impago = 1.0 (100%)
1.0 >= 0.7 → Riesgo ALTO
```

---

## 📝 Cómo Usar el Endpoint

### Desde el navegador o Postman:

1. **Obtener el ID del préstamo** desde la tabla de cobranza
2. **Llamar al endpoint:**
   ```
   GET https://rapicredit.onrender.com/api/v1/ai/training/ml-impago/calcular-detalle/{prestamo_id}
   ```
3. **Revisar la respuesta** para ver:
   - Todas las features calculadas
   - La probabilidad de impago
   - El criterio que determinó el nivel de riesgo

### Ejemplo con cédula:

Si necesitas buscar por cédula primero:
1. Buscar el préstamo por cédula en la BD
2. Obtener el `prestamo_id`
3. Usar ese ID en el endpoint

---

## 💡 Casos de Ejemplo

### Cliente con Riesgo ALTO (100%):
- **Features clave:**
  - `porcentaje_cuotas_pagadas: 0.0%`
  - `cuotas_vencidas_sin_pagar: 36`
  - `tasa_cumplimiento: 0.0%`
- **Resultado:** `probabilidad_impago = 1.0` → **Riesgo ALTO**

### Cliente con Riesgo BAJO (7%):
- **Features clave:**
  - `porcentaje_cuotas_pagadas: 95.0%` (casi todas pagadas)
  - `cuotas_vencidas_sin_pagar: 0` (no hay cuotas vencidas sin pagar)
  - `tasa_cumplimiento: 100.0%` (cumplimiento perfecto)
- **Resultado:** `probabilidad_impago = 0.07` → **Riesgo BAJO**

---

## 🔗 Endpoints Relacionados

1. **Cálculo detallado:** `GET /api/v1/ai/training/ml-impago/calcular-detalle/{prestamo_id}`
2. **Predicción simple:** `POST /api/v1/ai/training/ml-impago/predecir`
3. **Listar modelos:** `GET /api/v1/ai/training/ml-impago/modelos`

