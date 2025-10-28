# ⚠️ CAMBIO IMPORTANTE: Tasa de Interés como Sugerencia

## 🎯 Problema Identificado

**El sistema estaba aprobando préstamos automáticamente**, aplicando la tasa de interés sugerida sin permitir que el **humano** la revise o modifique.

Esto va contra el principio de **supervisión humana** en decisiones financieras.

---

## ✅ Solución Implementada

### 1️⃣ **La tasa de interés es SOLO una SUGERENCIA**

La evaluación de riesgo ahora:
- ✅ Genera una **sugerencia** de tasa de interés
- ✅ Sugiere condiciones (plazo, garantías, etc.)
- ❌ **NO aprueba automáticamente** el préstamo
- ❌ **NO aplica** la tasa automáticamente

### 2️⃣ **El humano (admin) decide**

El admin debe:
1. Revisar las sugerencias del sistema
2. Decidir si **acepta** la tasa sugerida o la **modifica**
3. Aprobar el préstamo con la tasa que considere apropiada

---

## 📋 Nuevo Flujo de Trabajo

### Paso 1: Evaluación de Riesgo
```bash
POST /api/v1/prestamos/{id}/evaluar-riesgo
```

**Respuesta:**
```json
{
  "decision_final": "APROBADO_AUTOMATICO",
  "requiere_aprobacion_manual": true,
  "mensaje": "✅ Préstamo candidato para aprobación. Debe ser aprobado manualmente con tasa sugerida.",
  "sugerencias": {
    "tasa_interes_sugerida": 15.0,
    "plazo_maximo_sugerido": 36,
    "enganche_minimo_sugerido": 10.0
  }
}
```

### Paso 2: Aprobación Manual (con tasa personalizable)
```bash
POST /api/v1/prestamos/{id}/aplicar-condiciones-aprobacion
```

**Body:**
```json
{
  "tasa_interes": 15.0,  // ⚠️ Puede ser diferente a la sugerencia
  "plazo_maximo": 24,    // ⚠️ Opcional: puede modificar
  "fecha_base_calculo": "2025-11-01",
  "estado": "APROBADO",
  "observaciones": "Aprobado con tasa personalizada por criterio del admin"
}
```

---

## 🔧 Cambios en el Código

### Archivo: `backend/app/api/v1/endpoints/prestamos.py`

**ANTES** (líneas 778-827):
```python
# Se aprobaba automáticamente
if evaluacion.decision_final == "APROBADO_AUTOMATICO":
    # Aplicaba tasa automáticamente
    prestamo.tasa_interes = condiciones["tasa_interes"]
    procesar_cambio_estado(prestamo, "APROBADO", ...)
```

**DESPUÉS** (líneas 781-789):
```python
# Solo indica que ES CANDIDATO para aprobación
if evaluacion.decision_final == "APROBADO_AUTOMATICO":
    logger.info("⚠️ El sistema SUGIERE aprobar, pero requiere decisión humana.")
    # NO aprueba automáticamente
    # El admin debe usar '/aplicar-condiciones-aprobacion' manualmente
```

---

## 🎯 Beneficios

1. ✅ **Supervisión humana** en decisiones financieras
2. ✅ **Flexibilidad** para modificar tasa según criterio
3. ✅ **Auditoría** clara: qué tasa se aplicó y por qué
4. ✅ **Control total** del proceso de aprobación

---

## 📝 Ejemplo de Uso

### Escenario: Juan García (Riesgo A)

1. **Evaluación** sugiere: `tasa_interes_sugerida: 15.0%`
2. **Admin** revisa y decide:
   - Opción A: Acepta 15%
   - Opción B: Modifica a 18% (más conservador)
   - Opción C: Rechaza el préstamo
3. **Aprobación** con la tasa elegida por el admin
4. **Amortización** se genera con la tasa FINAL aprobada

---

## ⚠️ Importante

**El préstamo #9 ya fue aprobado automáticamente** con la tasa 15%.

Para futuros préstamos:
1. La evaluación NO aprobará automáticamente
2. El admin verá las sugerencias
3. El admin debe aprobar manualmente con la tasa que considere

---

## 🔍 Verificación

Para verificar en DBeaver:

```sql
-- Ver la sugerencia de tasa en la evaluación
SELECT 
    prestamo_id,
    clasificacion_riesgo,
    tasa_interes_aplicada,  -- SUGERENCIA
    decision_final
FROM prestamos_evaluacion 
WHERE prestamo_id = 9;

-- Ver la tasa REAL aplicada al préstamo
SELECT 
    id,
    tasa_interes,  -- TASA REAL APLICADA
    estado
FROM prestamos 
WHERE id = 9;
```

**Comúnmente**: `tasa_interes_aplicada = tasa_interes` porque el admin aceptó la sugerencia.

**Diferencia**: Si admin modificó, habrá diferencia entre ambas.

