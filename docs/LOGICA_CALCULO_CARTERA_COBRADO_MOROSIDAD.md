# Lógica de Cálculo: Cartera, Cobrado y Cuentas por Cobrar

## Resumen
Los datos de **Cartera**, **Cobrado** y **Cuentas por Cobrar** en los gráficos del dashboard corresponden **SOLO a cada mes** de forma independiente, SIN acumulación.

---

## Definiciones Correctas

### 1. CARTERA (Pagos Programados)
**Cuotas con vencimiento programado en ese mes**, sin importar si fueron pagadas.

```sql
SELECT SUM(monto) 
FROM cuotas 
WHERE fecha_vencimiento BETWEEN inicio_mes AND fin_mes
  AND prestamo.estado = 'APROBADO';
```

**Ejemplo mes Febrero 2026:**
- Cuota 1: Vence 2026-02-05, Pago: NULL → Incluida en Cartera
- Cuota 2: Vence 2026-02-10, Pago: 2026-02-15 → Incluida en Cartera  
- Cuota 3: Vence 2026-01-15, Pago: 2026-02-05 → **NO incluida** (vence en enero)
- **Cartera Febrero = Cuota 1 + Cuota 2 = $600**

---

### 2. COBRADO (Pagos Conciliados)
**Cuotas con vencimiento EN ESE MES que fueron PAGADAS** (sin importar cuándo se pagaron).

```sql
SELECT SUM(monto) 
FROM cuotas 
WHERE fecha_vencimiento BETWEEN inicio_mes AND fin_mes
  AND fecha_pago IS NOT NULL
  AND prestamo.estado = 'APROBADO';
```

**Ejemplo mes Febrero 2026:**
- Cuota 1: Vence 2026-02-05, Pago: NULL → **NO incluida** en Cobrado
- Cuota 2: Vence 2026-02-10, Pago: 2026-02-15 → Incluida en Cobrado
- Cuota 3: Vence 2026-01-15, Pago: 2026-02-05 → **NO incluida** (vence en enero, se ignora)
- **Cobrado Febrero = Cuota 2 = $300**

---

### 3. CUENTAS POR COBRAR
**Lo que falta cobrar del mes** = Cartera - Cobrado

```sql
Cuentas por Cobrar = Cartera - Cobrado
```

**Ejemplo mes Febrero 2026:**
- Cartera Febrero: $600
- Cobrado Febrero: $300
- **Cuentas por Cobrar = $600 - $300 = $300** (lo que NO se pudo cobrar)

---

## Relación con concepto anterior

### Cambio: Morosidad → Cuentas por Cobrar

**Antes (INCORRECTO):**
- Morosidad = Cuotas vencidas que NO fueron pagadas (mezcla de conceptos)
- Podía dar resultados inconsistentes

**Ahora (CORRECTO):**
- Cuentas por Cobrar = Cartera - Cobrado
- **Siempre es >= 0** (no puede ser negativo)
- Representa lo que falta cobrar del mes

---

## Verificación de Coherencia

Para cada mes, se debe cumplir:

1. **Cartera ≥ 0** ✅
2. **Cobrado ≥ 0** ✅
3. **Cuentas por Cobrar ≥ 0** ✅ (porque Cobrado ≤ Cartera)
4. **Cobrado ≤ Cartera** ✅
5. **Cuentas por Cobrar = Cartera - Cobrado** ✅

**Ejemplo coherente:**
```
Febrero 2026:
- Cartera:          $1,500 (cuotas con vencimiento en febrero)
- Cobrado:          $  900 (cuotas de febrero que fueron pagadas)
- Cuentas por Cobrar: $ 600 (lo que falta cobrar de febrero)

Validación:
✅ Todos ≥ 0
✅ Cobrado ($900) ≤ Cartera ($1,500)
✅ Cuentas por Cobrar ($600) = Cartera ($1,500) - Cobrado ($900)
```

---

## Impacto en el Dashboard

### Gráfico "Evolución Mensual" (Cartera, Cobrado, Cuentas por Cobrar)
- **Eje X**: Meses (Abr 2025, May 2025, ..., Mar 2026)
- **Eje Y (barras azules)**: Cartera de ese mes = cuotas programadas
- **Eje Y (barras verdes)**: Cobrado en ese mes = cuotas de ese mes que se pagaron
- **Eje Y (línea roja)**: Cuentas por Cobrar = Cartera - Cobrado

**Interpretación correcta:**
> "En Febrero 2026, se programó cobrar $1,500 (barrita azul). Se cobraron $900 (barrita verde, SOLO de cuotas de febrero). Quedan $600 sin cobrar (línea roja)."

**Interpretación INCORRECTA:**
> "La línea roja es morosidad" ❌ → Ahora es "Cuentas por Cobrar"

---

## Implementación en Backend

El cálculo está en `backend/app/api/v1/endpoints/dashboard/kpis.py`, función `_compute_dashboard_admin()`:

```python
# CARTERA: Cuotas con fecha_vencimiento en este mes
cartera = db.scalar(
    select(func.coalesce(func.sum(Cuota.monto), 0))
    .select_from(Cuota)
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .where(
        Prestamo.estado == "APROBADO",
        Cuota.fecha_vencimiento >= inicio_d,
        Cuota.fecha_vencimiento <= fin_d,
    )
) or 0

# COBRADO: Cuotas con fecha_vencimiento en este mes que fueron pagadas
cobrado = db.scalar(
    select(func.coalesce(func.sum(Cuota.monto), 0))
    .select_from(Cuota)
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .where(
        Prestamo.estado == "APROBADO",
        Cuota.fecha_vencimiento >= inicio_d,
        Cuota.fecha_vencimiento <= fin_d,
        Cuota.fecha_pago.isnot(None),
    )
) or 0

# CUENTAS POR COBRAR = Cartera - Cobrado
cuentas_por_cobrar = cartera - cobrado
```

---

## Conclusión

✅ **Cada mes es independiente**  
✅ **NO hay acumulación entre períodos**  
✅ **Cobrado = SOLO cuotas con vencimiento en ese mes que se pagaron**  
✅ **Cuentas por Cobrar = Cartera - Cobrado (siempre >= 0)**  
✅ **Reemplaza el concepto anterior de Morosidad por uno más preciso**

