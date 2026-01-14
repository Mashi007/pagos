# 🔍 ANÁLISIS: Coherencia entre Columnas de `cuotas` y Reglas de Negocio

> **Fecha:** 2025-01-XX
> **Objetivo:** Verificar coherencia entre estructura de tabla `cuotas` y reglas de negocio

---

## 📋 ESTRUCTURA ACTUAL DE LA TABLA `cuotas`

### **Columnas Existentes (Según Modelo ORM Actualizado):**

| # | Columna | Tipo | Nullable | Descripción |
|---|---------|------|----------|-------------|
| 1 | `id` | INTEGER | NO | Primary Key |
| 2 | `prestamo_id` | INTEGER | NO | FK a `prestamos.id` (indexado) |
| 3 | `numero_cuota` | INTEGER | NO | Número de cuota (1, 2, 3, ...) |
| 4 | `fecha_vencimiento` | DATE | NO | Fecha límite de pago (indexado) |
| 5 | `fecha_pago` | DATE | YES | Fecha real cuando se pagó |
| 6 | `monto_cuota` | NUMERIC(12,2) | NO | Monto total programado |
| 7 | `saldo_capital_inicial` | NUMERIC(12,2) | NO | Saldo al inicio del período |
| 8 | `saldo_capital_final` | NUMERIC(12,2) | NO | Saldo al fin del período |
| 9 | `total_pagado` | NUMERIC(12,2) | YES | Suma acumulativa de pagos (default: 0.00) |
| 10 | `dias_mora` | INTEGER | YES | Días de mora (default: 0) |
| 11 | `dias_morosidad` | INTEGER | YES | Días de atraso (indexado, default: 0) |
| 12 | `estado` | VARCHAR(20) | NO | Estado (indexado, default: 'PENDIENTE') |
| 13 | `observaciones` | VARCHAR(500) | YES | Observaciones |
| 14 | `es_cuota_especial` | BOOLEAN | YES | Si es cuota especial |
| 15 | `creado_en` | TIMESTAMP | YES | Fecha de creación |
| 16 | `actualizado_en` | TIMESTAMP | YES | Fecha de actualización |

**Total: 16 columnas**

---

## 📋 REGLAS DE NEGOCIO DOCUMENTADAS

### **REGLA 1: Generación de Cuotas**
- ✅ Requiere: `prestamo_id`, `numero_cuota`, `fecha_vencimiento`, `monto_cuota`
- ✅ Coherencia: **OK** - Todas las columnas existen

### **REGLA 2: Cálculo de Cuotas (Método Francés)**
- ⚠️ **INCONSISTENCIA DETECTADA:**
  - Documentación menciona: `monto_capital`, `monto_interes`
  - Estructura actual: Solo `monto_cuota` (sin desglose)
  - **Estado:** Documentación desactualizada

### **REGLA 3: Aplicación de Pagos a Cuotas**
- ⚠️ **INCONSISTENCIA DETECTADA:**
  - Documentación menciona: `capital_pagado`, `interes_pagado`, `capital_pendiente`, `interes_pendiente`
  - Estructura actual: Solo `total_pagado` (sin desglose)
  - **Estado:** Documentación desactualizada

### **REGLA 4: Estados de Cuotas**
- ✅ Requiere: `estado`, `total_pagado`, `monto_cuota`, `fecha_vencimiento`
- ✅ Coherencia: **OK** - Todas las columnas existen

---

## ⚠️ INCONSISTENCIAS ENCONTRADAS

### **1. Documentación Desactualizada**

**Problema:**
- `Documentos/General/REGLAS_NEGOCIO_PAGOS_Y_CUOTAS.md` menciona columnas eliminadas:
  - `monto_capital`, `monto_interes`
  - `capital_pagado`, `interes_pagado`, `mora_pagada`
  - `capital_pendiente`, `interes_pendiente`
  - `monto_mora`, `tasa_mora`, `monto_morosidad`

**Impacto:**
- Confusión para desarrolladores
- Documentación no refleja la estructura real

**Solución:**
- Actualizar documentación para reflejar estructura simplificada

---

### **2. Propiedad `esta_vencida` con Estado Incorrecto**

**Problema:**
- En `amortizacion.py` línea 91:
  ```python
  return self.fecha_vencimiento < date.today() and self.estado != "PAGADA"
  ```
- El estado en BD es `"PAGADO"` (masculino), no `"PAGADA"` (femenino)

**Impacto:**
- La propiedad puede retornar valores incorrectos

**Solución:**
- Corregir a `self.estado != "PAGADO"`

---

### **3. Columna `dias_mora` Siempre 0**

**Problema:**
- `dias_mora` siempre se establece en 0 (mora desactivada)
- Pero `dias_morosidad` se calcula automáticamente
- Hay redundancia potencial

**Análisis:**
- `dias_mora`: Siempre 0 (mora desactivada)
- `dias_morosidad`: Calculado automáticamente (útil para reportes)
- **Decisión:** Mantener `dias_morosidad`, considerar eliminar `dias_mora` si siempre es 0

---

### **4. Falta de Restricción CHECK para `total_pagado`**

**Problema:**
- No hay restricción que valide `total_pagado >= 0`
- No hay restricción que valide `total_pagado <= monto_cuota * factor_tolerancia`

**Impacto:**
- Posibilidad de valores negativos o sobrepagos excesivos sin validación a nivel BD

**Solución:**
- Agregar CHECK constraint: `total_pagado >= 0`
- Considerar CHECK constraint: `total_pagado <= monto_cuota * 1.5` (tolerancia para sobrepagos)

---

### **5. Falta de Índice Compuesto**

**Problema:**
- Consultas frecuentes filtran por `prestamo_id` y `estado` o `fecha_vencimiento`
- No hay índices compuestos para optimizar estas consultas

**Impacto:**
- Consultas más lentas cuando se filtran múltiples columnas

**Solución:**
- Crear índice compuesto: `(prestamo_id, estado)`
- Crear índice compuesto: `(prestamo_id, fecha_vencimiento)`

---

## ✅ MEJORAS PROPUESTAS

### **MEJORA 1: Actualizar Documentación**

**Archivo:** `Documentos/General/REGLAS_NEGOCIO_PAGOS_Y_CUOTAS.md`

**Cambios:**
- Eliminar referencias a columnas eliminadas
- Actualizar ejemplos de código para usar solo `monto_cuota` y `total_pagado`
- Actualizar descripción de estructura de tabla

---

### **MEJORA 2: Corregir Propiedad `esta_vencida`**

**Archivo:** `backend/app/models/amortizacion.py`

**Cambio:**
```python
# ANTES:
return self.fecha_vencimiento < date.today() and self.estado != "PAGADA"

# DESPUÉS:
return self.fecha_vencimiento < date.today() and self.estado != "PAGADO"
```

---

### **MEJORA 3: Agregar Restricciones CHECK**

**Script SQL:**
```sql
-- Validar que total_pagado no sea negativo
ALTER TABLE public.cuotas 
ADD CONSTRAINT check_total_pagado_no_negativo 
CHECK (total_pagado >= 0);

-- Validar que monto_cuota sea positivo
ALTER TABLE public.cuotas 
ADD CONSTRAINT check_monto_cuota_positivo 
CHECK (monto_cuota > 0);

-- Validar que total_pagado no exceda monto_cuota en más del 50% (tolerancia para sobrepagos)
ALTER TABLE public.cuotas 
ADD CONSTRAINT check_total_pagado_razonable 
CHECK (total_pagado <= monto_cuota * 1.5);
```

---

### **MEJORA 4: Crear Índices Compuestos**

**Script SQL:**
```sql
-- Índice para consultas por préstamo y estado
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_estado 
ON public.cuotas(prestamo_id, estado);

-- Índice para consultas por préstamo y fecha de vencimiento
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_fecha_vencimiento 
ON public.cuotas(prestamo_id, fecha_vencimiento);

-- Índice para consultas de morosidad
CREATE INDEX IF NOT EXISTS idx_cuotas_morosidad 
ON public.cuotas(dias_morosidad, estado) 
WHERE dias_morosidad > 0;
```

---

### **MEJORA 5: Evaluar Eliminación de `dias_mora`**

**Análisis:**
- `dias_mora` siempre es 0 (mora desactivada)
- `dias_morosidad` se calcula automáticamente y es útil

**Recomendación:**
- Si `dias_mora` siempre es 0, considerar eliminarlo
- Mantener solo `dias_morosidad` que es más útil

**Script SQL (si se decide eliminar):**
```sql
ALTER TABLE public.cuotas DROP COLUMN IF EXISTS dias_mora;
```

---

### **MEJORA 6: Agregar Validación de Estados**

**Script SQL:**
```sql
-- Restricción para validar estados válidos
ALTER TABLE public.cuotas 
ADD CONSTRAINT check_estado_valido 
CHECK (estado IN ('PENDIENTE', 'PAGADO', 'ATRASADO', 'PARCIAL', 'ADELANTADO'));
```

---

### **MEJORA 7: Agregar Validación de Fechas**

**Script SQL:**
```sql
-- Validar que fecha_pago sea posterior o igual a fecha_vencimiento (si existe)
-- Nota: Esto puede ser demasiado restrictivo si se permiten pagos adelantados
-- Se puede hacer opcional o con lógica más compleja
```

---

## 📊 RESUMEN DE COHERENCIA

### **✅ COHERENTE:**
- Estructura básica de columnas esenciales
- Relaciones con otras tablas (Foreign Keys)
- Campos requeridos para reglas de negocio principales

### **⚠️ INCONSISTENCIAS:**
1. Documentación desactualizada (menciona columnas eliminadas)
2. Propiedad `esta_vencida` usa estado incorrecto
3. Falta de restricciones CHECK para validación de datos
4. Falta de índices compuestos para optimización
5. `dias_mora` siempre 0 (redundante con `dias_morosidad`)

### **🔧 MEJORAS PROPUESTAS:**
1. Actualizar documentación
2. Corregir propiedad `esta_vencida`
3. Agregar restricciones CHECK
4. Crear índices compuestos
5. Evaluar eliminación de `dias_mora`
6. Agregar validación de estados
7. Considerar validación de fechas

---

## 🎯 PRIORIDAD DE MEJORAS

### **ALTA PRIORIDAD:**
1. ✅ Corregir propiedad `esta_vencida` (bug funcional)
2. ✅ Agregar restricción CHECK para `total_pagado >= 0`
3. ✅ Agregar validación de estados válidos

### **MEDIA PRIORIDAD:**
4. ✅ Actualizar documentación
5. ✅ Crear índices compuestos

### **BAJA PRIORIDAD:**
6. ✅ Evaluar eliminación de `dias_mora`
7. ✅ Considerar validación de fechas

---

## ✅ CONCLUSIÓN

La estructura actual de `cuotas` es **coherente** con las reglas de negocio principales, pero hay:
- **Documentación desactualizada** que necesita corrección
- **Mejoras de validación** que se pueden agregar
- **Optimizaciones** de índices que se pueden implementar

Las mejoras propuestas mejorarán la integridad de datos, rendimiento y mantenibilidad del sistema.
