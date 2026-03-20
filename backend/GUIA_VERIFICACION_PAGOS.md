# Verificación Integral: ¿Están todos los pagos cargados en sus cuotas?

## Descripción del Problema

El objetivo es garantizar que **todos los pagos registrados en la tabla `pagos`** estén correctamente vinculados y aplicados a sus **cuotas correspondientes** a través de la tabla `cuota_pagos`.

### Tablas Involucradas

1. **pagos**: Registro de todas las transacciones de pago
   - Campos clave: `id`, `prestamo_id`, `monto_pagado`, `fecha_pago`, `referencia_pago`, `estado`

2. **cuotas**: Todas las cuotas del sistema (mensuales, quincenales, especiales)
   - Campos clave: `id`, `prestamo_id`, `numero_cuota`, `monto_cuota`, `estado`, `total_pagado`

3. **cuota_pagos**: Tabla JOIN que registra la aplicación de cada pago a cada cuota
   - Campos clave: `cuota_id`, `pago_id`, `monto_aplicado`, `fecha_aplicacion`, `orden_aplicacion`

---

## Queries Principales

### Query 1: Pagos NO vinculados a cuotas (CRÍTICA)
```sql
-- Identifica pagos que NO están en la tabla cuota_pagos
-- Estos pagos representan dinero "perdido" en el sistema
```

**Casos de uso:**
- Auditar pagos que nunca fueron procesados
- Encontrar pagos descargados parcialmente
- Identificar dinero no contabilizado

**Interpretación:**
- Si `total_aplicado_a_cuotas = 0` → Pago completamente perdido
- Si `diferencia_no_aplicada > 0` → Pago parcialmente aplicado

---

### Query 2: Pagos completamente descargados (100%)
```sql
-- Pagos que han sido totalmente aplicados a sus cuotas
-- Estos son "limpios" y no requieren acción
```

**Interpretación:**
- `saldo_sin_aplicar = 0` → Pago OK ✓
- `saldo_sin_aplicar > 0` → Pago parcialmente cargado

---

### Query 3: Pagos parcialmente aplicados
```sql
-- Pagos que tienen PARTE aplicada a cuotas pero no todo
-- Requiere investigación para completar la carga
```

**Interpretación:**
- `porcentaje_aplicado < 100` → Saldo pendiente
- `numero_cuotas` → Cuántas cuotas tocó el pago

---

### Query 4: Pagos SIN REGISTRO en cuota_pagos (RIESGO ALTO)
```sql
-- Pagos que existen en BD pero NUNCA fueron asignados a cuota
-- Estado: COMPLETAMENTE PERDIDO
```

**Casos de uso:**
- Encontrar pagos que necesitan aplicación manual
- Auditar integridad de datos post-migración
- Identificar pagos en estado "con_errores"

---

### Query 5: Pagos con/sin referencia_pago
```sql
-- Agrupa pagos válidos (con referencia) vs inválidos (sin referencia)
-- La referencia_pago es obligatoria para la carga
```

**Interpretación:**
- `SIN REFERENCIA` = Pago incompleto (no puede procesarse)
- `CON REFERENCIA` = Pago válido (debería estar en cuota_pagos)

---

### Query 6: Cobertura por estado de pago
```sql
-- Analiza qué estado de pago tiene mejor cobertura en cuotas
-- Identifica si ciertos estados requieren más atención
```

**Estados típicos:**
- `conciliado` = Pagos procesados y sincronizados
- `pendiente_conciliacion` = En cola de procesamiento
- `con_errores` = Requiere corrección manual
- `rechazado` = Pago no válido

---

### Query 7: Análisis por préstamo
```sql
-- Responde: "Para este préstamo, ¿todas sus cuotas recibieron pagos?"
-- Identifica préstamos con cuotas huérfanas
```

**Casos problemáticos:**
- `cuotas_sin_pagos > 0` → Falta aplicar pagos
- `total_pagos_asignados = 0` → Préstamo nunca procesado
- `total_monto_pagado < monto_solicitado` → Pago incompleto

---

### Query 8: Cuotas SIN pagos asignados (CRÍTICA)
```sql
-- Todas las cuotas que NO tienen ningún pago en cuota_pagos
-- Estas cuotas permanecen pendientes por falta de carga
```

**Interpretación:**
- Si `estado = PAGADA` pero no hay pagos → INCONSISTENCIA
- Si `estado = PENDIENTE` pero hay pagos en `total_pagado` → Datos desincronizados

---

### Query 9: Duplicados en cuota_pagos
```sql
-- Detecta si una misma cuota recibió el MISMO pago múltiples veces
-- Riesgo de sobre-aplicación y doble conteo
```

**Interpretación:**
- `cantidad_veces_aplicado > 1` → Sobre-aplicación
- `total_monto_aplicado > monto_cuota` → Error crítico

---

### Query 10: Inconsistencias de montos
```sql
-- Compara monto_cuota vs total_aplicado en cuota_pagos
-- Identifica desajustes en cálculos
```

**Casos problemáticos:**
- `saldo_restante < 0` → Sobre-pago (monto aplicado > monto_cuota)
- `estado = PAGADA` pero `saldo_restante > 0` → Cuota marcada como pagada sin saldo cubierto

---

### Query 11: Dashboard ejecutivo
```sql
-- Resumen de sincronización en un vistazo
-- KPIs: Total de pagos, cuotas, cobertura, montos
```

**Métricas clave:**
- % de pagos con cuotas asignadas
- % de cuotas con pagos asignados
- Balance de montos (pagos vs cuotas)

---

### Query 12: Pagos huérfanos (sin préstamo válido)
```sql
-- Pagos que:
--   1. No tienen prestamo_id asignado
--   2. Su prestamo_id NO existe en tabla prestamos
-- Estos pagos no pueden ser aplicados a cuota
```

**Interpretación:**
- `prestamo_id IS NULL` → Necesita asignación manual
- `Préstamo no existe` → Error de integridad referencial

---

### Query 13: Resumen por cliente
```sql
-- Para cada cliente, muestra:
--   - Total de pagos realizados
--   - Total de cuotas del préstamo
--   - Cuántos pagos fueron asignados
--   - Cuántas cuotas nunca recibieron pago
-- Sorting por porcentaje de asignación (ASC = problemas primero)
```

---

### Query 14: Audit de pagos recientes SIN cuotas
```sql
-- Últimos 30 días
-- Pagos que aún no fueron asignados a cuotas
-- Útil para identificar rezagos en el pipeline de procesamiento
```

---

## Cómo Usar Este Diagnóstico

### Paso 1: Ejecuta el Query 11 (Dashboard Ejecutivo)
```
Este te da el panorama general:
- ¿Cuántos pagos hay?
- ¿Cuántos están asignados?
- ¿Qué hay en cuota_pagos?
```

### Paso 2: Ejecuta Query 1 (Pagos NO vinculados)
```
Si el resultado es grande:
- Identifica cuáles son los pagos problemáticos
- Agrupa por estado, prestamo_id, fecha
```

### Paso 3: Ejecuta Query 8 (Cuotas SIN pagos)
```
Si el resultado es grande:
- Revisa si debería haber pagos aplicados
- Verifica si el estado de la cuota es consistente
```

### Paso 4: Ejecuta Query 10 (Inconsistencias de montos)
```
Si el resultado es grande:
- Identifica posibles errores de cálculo
- Revisa cuotas con sobre-pago o sub-pago
```

### Paso 5: Ejecuta Query 13 (Resumen por cliente)
```
Para clientes específicos:
- Verifica el porcentaje de asignación
- Identifica qué falta por hacer
```

---

## Interpretación Rápida

### Escenario 1: ¿TODO OK?
```
- Query 1: 0 resultados (no hay pagos sin cuotas)
- Query 4: 0 resultados (no hay pagos perdidos)
- Query 8: Pocas cuotas sin pagos (solo las que verdaderamente no han sido pagadas)
- Query 10: 0 inconsistencias
- Query 13: Todos los clientes con ~100% de asignación
```

### Escenario 2: Pagos no aplicados (PROBLEMA)
```
- Query 1: Muchos resultados con diferencia_no_aplicada > 0
- Query 4: Pagos que existen pero nunca fueron asignados
- Acción: Ejecutar rutina de aplicación de pagos pendientes
```

### Escenario 3: Cuotas sin pagos (PROBLEMA)
```
- Query 8: Muchas cuotas pendientes
- Query 7: Préstamos con muchas cuotas_sin_pagos
- Acción: Revisar si los pagos existen pero no fueron asignados
```

### Escenario 4: Inconsistencias de montos (CRÍTICO)
```
- Query 10: Cuotas con saldo_restante < 0 (sobre-pago)
- Query 9: Duplicados en cuota_pagos
- Acción: Auditar aplicación de pagos, posibles errores FIFO
```

---

## Recomendaciones

### 1. Crear Índices
```sql
CREATE INDEX idx_pagos_prestamo_id ON pagos(prestamo_id);
CREATE INDEX idx_cuota_pagos_pago_id ON cuota_pagos(pago_id);
CREATE INDEX idx_cuota_pagos_cuota_id ON cuota_pagos(cuota_id);
```

### 2. Validaciones Continuas
- Ejecutar Query 11 cada hora (automatizar)
- Alertar si hay pagos SIN cuotas > threshold

### 3. Auditoría Mensual
- Ejecutar Query 13 para cada cliente
- Identificar patrones de no-asignación

### 4. Recuperación de Datos
Si encuentras pagos perdidos:
```sql
-- Insertar en cuota_pagos para recuperar pagos perdidos
-- (Requiere lógica específica del negocio para asignar a cuota correcta)
```

---

## Campos Clave en Diagnóstico

| Campo | Significado | Acción si problema |
|-------|-------------|-------------------|
| `total_aplicado_a_cuotas` | Monto pagado desde `cuota_pagos` | Si = 0: Pago perdido |
| `diferencia_no_aplicada` | Monto del pago sin asignar | Si > 0: Aplicar a cuota |
| `cuotas_sin_pagos` | Cuantas cuotas NO recibieron pagos | Si > 0: Investigar por qué |
| `saldo_restante` | Diferencia entre monto_cuota y lo pagado | Si < 0: Sobre-pago |
| `porcentaje_asignado` | % de pagos que llegaron a cuota_pagos | Si < 100: Brecha de carga |

---

## Conclusión

Este set de queries proporciona visibilidad completa sobre:
1. ✅ Qué pagos están correctamente aplicados
2. ❌ Qué pagos están perdidos o parcialmente aplicados
3. ⚠️ Qué cuotas nunca recibieron pagos
4. 🔄 Qué inconsistencias existen en montos

Ejecuta el Query 11 primero para entender el estado general, luego profundiza con los queries específicos según lo que encuentres.
