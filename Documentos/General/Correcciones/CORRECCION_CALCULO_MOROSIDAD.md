# 🔧 Corrección: Cálculo de Morosidad Real

## Fecha: 2025-11-05

---

## ❌ Problema Identificado

**La morosidad siempre aumenta y nunca disminuye, aunque haya pagos**

El usuario reportó que la línea de morosidad en el gráfico "MONITOREO FINANCIERO" nunca disminuye, incluso cuando hay cobros (pagos).

### Causa Raíz

El cálculo anterior solo sumaba cuotas vencidas con `estado != 'PAGADO'`, pero **NO restaba los pagos aplicados** a esas cuotas. Esto causaba que:

1. La morosidad solo podía aumentar (nuevas cuotas vencidas)
2. Nunca podía disminuir (pagos no se restaban)
3. El gráfico mostraba una línea siempre creciente

---

## ✅ Solución Implementada

### Nueva Fórmula de Morosidad

**Morosidad Real = Cuotas Vencidas - Pagos Aplicados a Cuotas Vencidas**

```
Morosidad = SUM(monto_cuota de cuotas vencidas)
          - SUM(monto_aplicado de pagos a cuotas vencidas)
```

### Cambios en el Código

#### 1. Query Optimizada (Líneas 3590-3650)

**Antes:**
```sql
SELECT
    COALESCE(SUM(c.monto_cuota), 0) as morosidad
FROM cuotas c
WHERE c.fecha_vencimiento <= ultimo_dia_mes
  AND c.estado != 'PAGADO'
```

**Después:**
```sql
WITH cuotas_vencidas AS (
    SELECT SUM(monto_cuota) as total_cuotas_vencidas
    FROM cuotas c
    WHERE c.fecha_vencimiento <= ultimo_dia_mes
      AND c.estado != 'PAGADO'
),
pagos_aplicados AS (
    SELECT SUM(pc.monto_aplicado) as total_pagado
    FROM pago_cuotas pc
    INNER JOIN cuotas c ON pc.cuota_id = c.id
    WHERE c.fecha_vencimiento <= ultimo_dia_mes
      AND c.estado != 'PAGADO'
      AND EXISTS (
          SELECT 1 FROM pagos p
          WHERE p.id = pc.pago_id
            AND p.fecha_pago <= ultimo_dia_mes
            AND p.activo = TRUE
      )
)
SELECT
    GREATEST(0, cuotas_vencidas.total_cuotas_vencidas - pagos_aplicados.total_pagado) as morosidad
FROM cuotas_vencidas, pagos_aplicados
```

#### 2. Fallback Actualizado (Líneas 3667-3700)

El método fallback también fue actualizado para restar pagos aplicados.

---

## 📊 Comportamiento Esperado

### Antes (Incorrecto):
- Ene 2025: Morosidad = $100,000
- Feb 2025: Morosidad = $110,000 (nuevas cuotas vencidas)
- Mar 2025: Morosidad = $120,000 (aumenta aunque haya pagos)
- **❌ Nunca disminuye**

### Después (Correcto):
- Ene 2025: Morosidad = $100,000
- Feb 2025: Morosidad = $110,000 (nuevas cuotas vencidas)
- Mar 2025: Morosidad = $95,000 (aumenta por nuevas cuotas, pero disminuye por pagos)
- **✅ Puede disminuir cuando hay pagos suficientes**

---

## 🔍 Cómo Funciona

### 1. Cuotas Vencidas
- Suma todas las cuotas con `fecha_vencimiento <= ultimo_dia_mes`
- Filtra: `estado != 'PAGADO'`
- Filtra: `prestamos.estado = 'APROBADO'`

### 2. Pagos Aplicados
- Suma todos los pagos aplicados a cuotas vencidas hasta el final del mes
- Usa la tabla `pago_cuotas` para relacionar pagos con cuotas
- Solo considera pagos con `fecha_pago <= ultimo_dia_mes`
- Solo considera pagos activos (`activo = TRUE`)

### 3. Cálculo Final
- `Morosidad = MAX(0, Cuotas Vencidas - Pagos Aplicados)`
- El `MAX(0, ...)` asegura que la morosidad nunca sea negativa

---

## 📝 Notas Técnicas

### Tabla `pago_cuotas`
Esta tabla relaciona pagos con cuotas y almacena el `monto_aplicado`:
- `pago_id`: ID del pago
- `cuota_id`: ID de la cuota
- `monto_aplicado`: Monto del pago aplicado a esa cuota

### Consideraciones

1. **Pagos Parciales**: Si una cuota tiene pagos parciales, el `monto_aplicado` se suma correctamente
2. **Múltiples Pagos**: Si una cuota tiene múltiples pagos, todos se suman
3. **Pagos Futuros**: Los pagos con fecha posterior al final del mes NO se consideran
4. **Cuotas Pagadas**: Las cuotas con `estado = 'PAGADO'` no se incluyen en cuotas vencidas

---

## ✅ Beneficios

1. **Morosidad Real**: Refleja el saldo real pendiente de cobro
2. **Puede Disminuir**: La línea puede bajar cuando hay pagos suficientes
3. **Más Preciso**: Considera los pagos realmente aplicados a cuotas vencidas
4. **Mejor Visualización**: El gráfico muestra tendencias reales de morosidad

---

## 🔍 Verificación

### Próximos Pasos

1. **Monitorear el gráfico** después del despliegue
2. **Verificar que la morosidad disminuye** en meses con pagos altos
3. **Comparar con datos reales** para confirmar precisión

### Indicadores de Éxito

- ✅ La línea de morosidad puede disminuir cuando hay pagos
- ✅ La morosidad refleja el saldo real pendiente
- ✅ El gráfico muestra tendencias reales (no solo aumento constante)

---

**Estado:** ✅ Corregido y listo para despliegue

