# 📊 Explicación: Relación entre Morosidad y Cobros

## ❓ Pregunta: ¿La morosidad del siguiente mes acumulada resta de los cobros del mes presente?

**Respuesta: NO, son cálculos independientes.**

---

## ✅ Cálculo de Cobros (Monto Pagado)

**Cobros del mes presente** se calculan así:
```sql
SELECT SUM(monto_pagado)
FROM pagos
WHERE fecha_pago >= primer_dia_mes
  AND fecha_pago <= ultimo_dia_mes
  AND activo = TRUE
```

**Características:**
- ✅ Solo cuenta pagos con `fecha_pago` en ese mes específico
- ✅ NO depende de la morosidad
- ✅ NO se ve afectado por cuotas de meses futuros
- ✅ Es independiente de cuándo vencen las cuotas

**Ejemplo:**
- Si un cliente paga $500 el 15 de enero, ese $500 aparece en los cobros de enero
- No importa si ese pago se aplica a una cuota de enero, febrero o marzo

---

## ✅ Cálculo de Morosidad (NO Acumulada)

**Morosidad del mes** se calcula así:
```sql
SELECT SUM(monto_cuota - total_pagado)
FROM cuotas
WHERE fecha_vencimiento >= primer_dia_mes
  AND fecha_vencimiento <= ultimo_dia_mes
  AND estado != 'PAGADO'
```

**Características:**
- ✅ Solo cuenta cuotas que **vencieron** en ese mes específico
- ✅ NO es acumulada (no incluye meses anteriores)
- ✅ NO afecta los cobros del mes presente
- ✅ Es independiente de cuándo se hicieron los pagos

**Ejemplo:**
- Si una cuota de febrero vence el 10 de febrero por $500, y solo se pagó $200:
  - Morosidad de febrero = $500 - $200 = $300
- No importa si el pago de $200 se hizo en enero o febrero

---

## 🔍 ¿Cómo se Relacionan?

### Caso 1: Pago en Enero para Cuota de Febrero

**Escenario:**
- Cuota de febrero: $500 (vence 10 de febrero)
- Pago en enero: $200 (aplicado a cuota de febrero)

**Resultado:**
- **Cobros de enero:** $200 ✅ (porque el pago fue en enero)
- **Morosidad de febrero:** $300 ✅ (porque $500 - $200 = $300)
- **Cobros de febrero:** $0 ✅ (no hubo pagos en febrero)

**Conclusión:** Son independientes, no se restan entre sí.

---

### Caso 2: Pago en Febrero para Cuota de Enero (Atrasada)

**Escenario:**
- Cuota de enero: $500 (venció 10 de enero, no pagada)
- Pago en febrero: $500 (aplicado a cuota de enero)

**Resultado:**
- **Cobros de enero:** $0 ✅ (no hubo pagos en enero)
- **Morosidad de enero:** $500 ✅ (cuota que venció en enero, no pagada)
- **Cobros de febrero:** $500 ✅ (el pago fue en febrero)
- **Morosidad de febrero:** $0 ✅ (no hay cuotas que vencieron en febrero sin pagar)

**Conclusión:** Cada métrica refleja su mes específico, no se afectan entre sí.

---

## ⚠️ ¿Hay Algún Problema?

**NO**, los cálculos son correctos e independientes:

1. **Cobros:** Solo dependen de `fecha_pago` en el mes
2. **Morosidad:** Solo depende de `fecha_vencimiento` en el mes y `total_pagado` de esas cuotas

**No hay resta entre ellos:**
- La morosidad NO resta de los cobros
- Los cobros NO afectan la morosidad (excepto que reducen `total_pagado` de las cuotas)

---

## 📈 Ejemplo Completo

**Enero 2025:**
- Cobros: $68.051 (todos los pagos realizados en enero)
- Morosidad: $4.275 (cuotas que vencieron en enero y no se pagaron completamente)

**Febrero 2025:**
- Cobros: $50.000 (todos los pagos realizados en febrero)
- Morosidad: $3.000 (cuotas que vencieron en febrero y no se pagaron completamente)

**¿La morosidad de febrero afecta los cobros de enero?**
- **NO**, son cálculos completamente independientes.

**¿Los cobros de febrero reducen la morosidad de febrero?**
- **SÍ**, indirectamente: si un pago de febrero se aplica a una cuota de febrero, reduce `total_pagado` de esa cuota, lo que reduce la morosidad de febrero.

Pero esto es correcto: si pagas una cuota, la morosidad debe reducirse.

