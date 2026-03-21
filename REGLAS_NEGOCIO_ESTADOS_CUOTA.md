# Reglas de Negocio - Estados de Cuota

## Definiciones Claras de Estados

### 1. PENDIENTE
**Condición:** 
- Fecha de vencimiento >= hoy
- Monto pagado < monto de cuota

**Ejemplo:**
- Cuota vence el 20/03/2026
- Hoy es 19/03/2026
- Pagado: $0
- **Estado: PENDIENTE**

### 2. VENCIDA
**Condición:**
- Fecha de vencimiento < hoy (ha pasado la fecha de vencimiento)
- Monto pagado < monto de cuota
- Días transcurridos desde vencimiento <= 90 días

**Ejemplo:**
- Cuota vence el 20/03/2026
- Hoy es 21/03/2026 (1 día después del vencimiento)
- Pagado: $0
- **Estado: VENCIDA**

**Otro ejemplo:**
- Cuota vence el 20/03/2026
- Hoy es 15/06/2026 (87 días después del vencimiento)
- Pagado: $0
- **Estado: VENCIDA**

### 3. MORA
**Condición:**
- Fecha de vencimiento + 90 días < hoy (han pasado más de 90 días desde vencimiento)
- Monto pagado < monto de cuota

**Ejemplo:**
- Cuota vence el 20/03/2026
- Hoy es 20/06/2026 (92 días después del vencimiento - fecha vencimiento + 90 días = 19/06/2026)
- Pagado: $0
- **Estado: MORA**

### 4. PAGADO
**Condición:**
- Monto pagado >= monto de cuota - 0.01 (tolerancia por redondeo)

**Ejemplo:**
- Monto de cuota: $260.00
- Pagado: $260.00 o más
- **Estado: PAGADO** (independiente de fecha)

---

## Cálculo de Días de Mora

```
dias_mora = (hoy - fecha_vencimiento).days
```

Si `dias_mora <= 0` → está pendiente
Si `0 < dias_mora <= 90` → está vencida
Si `dias_mora > 90` → está en mora

---

## Matriz de Transiciones de Estado Permitidas

| De → A | PENDIENTE | VENCIDA | MORA | PAGADO | PAGO_ADELANTADO |
|--------|-----------|---------|------|--------|-----------------|
| **PENDIENTE** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **VENCIDA** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **MORA** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **PAGADO** | ❌ | ❌ | ❌ | ✅ | ❌ |
| **PAGO_ADELANTADO** | ❌ | ❌ | ❌ | ✅ | ✅ |

---

## Archivos que Implementan la Lógica

### 1. **backend/app/services/cuota_estado.py** ⭐ FUENTE ÚNICA DE VERDAD
- Función: `estado_cuota_para_mostrar(total_pagado, monto_cuota, fecha_vencimiento, fecha_corte)`
- **Responsabilidad:** Calcular estado de una cuota basado en:
  - total_pagado (float)
  - monto_cuota (float)
  - fecha_vencimiento (date)
  - fecha_corte (date) - fecha de "hoy" para comparación

### 2. **backend/app/api/v1/endpoints/pagos.py**
- Función: `_clasificar_nivel_mora()` - **DUPLICADA** (debe consolidarse)
- Ubicación: Líneas 211-230
- Uso: Validación de transiciones de estado

### 3. **backend/app/api/v1/endpoints/estado_cuenta_publico.py**
- Líneas: 243, 311
- Uso: Generar estado de cuenta público (consulta por cédula)
- Llama: `estado_cuota_para_mostrar()`

### 4. **backend/app/api/v1/endpoints/prestamos.py**
- Líneas: 880, 979
- Uso: Tabla de amortización en detalles de préstamo
- Llama: `estado_cuota_para_mostrar()`

### 5. **backend/app/services/estado_cuenta_pdf.py**
- Líneas: 413, 447
- Uso: Generación de PDF de estado de cuenta
- Llama: `estado_cuota_para_mostrar()`

### 6. **backend/app/services/conciliacion_automatica_service.py**
- Función: `calcular_estado_actualizado()` - Líneas 84-97
- **Problema:** Implementa su propia lógica, no usa `cuota_estado.py`
- Debe: Actualizar para usar función centralizada

### 7. **backend/app/api/v1/endpoints/cobros.py**
- Función: Aplicación de pagos reportados a cuotas
- Líneas: 495-551
- Debe: Recalcular estado usando función centralizada

---

## Cambios Necesarios

### CRÍTICOS (Antes de producción)

1. ✅ **Consolidar lógica de `_clasificar_nivel_mora()`**
   - Eliminar duplicidad en `pagos.py`
   - Usar siempre `cuota_estado.py` como fuente única

2. ✅ **Actualizar `conciliacion_automatica_service.py`**
   - Cambiar función `calcular_estado_actualizado()` para usar `estado_cuota_para_mostrar()`
   - Pruebas para casos límite (exactamente 90 días, etc.)

3. ✅ **Validar transiciones de estado**
   - Asegurar que MORA solo ocurre cuando `dias_mora > 90`
   - Implementar validación en aplicación de pagos

### MEJORAS (Post-implementación)

1. 📝 **Documentación**
   - Agregar docstrings a `estado_cuota_para_mostrar()` con ejemplos
   - Documentar matriz de transiciones en código

2. 🧪 **Tests**
   - Test unitarios para cada estado
   - Test de casos límite (vencimiento exacto, 90 días exactos, etc.)
   - Test de transiciones de estado

3. 🔍 **Auditoría**
   - Revisar cuotas existentes en BD
   - Validar que estados actuales son correctos
   - Migrar estados inconsistentes si es necesario

---

## Ejemplos Prácticos por Fecha

### Cuota con vencimiento 20/03/2026 y monto $260

| Fecha Hoy | Días Transcurridos | Pagado | Estado Correcto |
|-----------|-------------------|--------|-----------------|
| 19/03/2026 | -1 | $0 | **PENDIENTE** |
| 20/03/2026 | 0 | $0 | **PENDIENTE** |
| 21/03/2026 | 1 | $0 | **VENCIDA** |
| 15/06/2026 | 87 | $0 | **VENCIDA** |
| 19/06/2026 | 91 | $0 | **MORA** |
| 20/06/2026 | 92 | $0 | **MORA** |
| 21/03/2026 | 1 | $260 | **PAGADO** |
| 15/06/2026 | 87 | $260 | **PAGADO** |
| 19/06/2026 | 91 | $260 | **PAGADO** |

---

## Aplicación en Informes

### Estado de Cuenta Público (`/pagos/rapicredit-estadocuenta`)
✅ Usa `estado_cuota_para_mostrar()` - Correctamente implementado

### Estado de Cuenta PDF (nuevo endpoint)
✅ Usa `estado_cuota_para_mostrar()` - Correctamente implementado

### Tabla de Amortización (Detalles de Préstamo)
✅ Usa `estado_cuota_para_mostrar()` - Correctamente implementado

### Dashboard / Reportes
📋 Debe revisarse y actualizarse si existen cálculos propios

---

## Referencias en Código

### Búsquedas útiles:
```bash
# Buscar uso de "MORA"
grep -r "MORA" backend/

# Buscar cálculo de dias_mora
grep -r "dias_mora" backend/

# Buscar estado_cuota_para_mostrar
grep -r "estado_cuota_para_mostrar" backend/
```

---

## Historial de Cambios

| Fecha | Cambio | Usuario |
|-------|--------|---------|
| 20/03/2026 | Documentación inicial de reglas | Sistema |

---

## Preguntas Frecuentes

**P: ¿Qué pasa si una cuota se paga exactamente en la fecha de vencimiento?**
A: Se considera PENDIENTE hasta que pase la medianoche. A partir del 21/03 sería VENCIDA.

**P: ¿Qué pasa si se paga una cuota VENCIDA?**
A: Transiciona a PAGADO. El registro histórico debe mantener que estuvo VENCIDA.

**P: ¿Se pueden revertir pagos?**
A: Sí, una cuota PAGADA puede revertir a su estado anterior (VENCIDA, MORA, etc.) según fecha de vencimiento.

**P: ¿Cómo afecta esto a los reportes?**
A: Los estados se recalculan dinámicamente basados en fecha de vencimiento y pagos aplicados. Los reportes siempre mostrarán estado actual.

---

