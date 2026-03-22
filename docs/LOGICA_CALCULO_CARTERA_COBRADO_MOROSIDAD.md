# Lógica de Cálculo: Cartera, Cobrado y Morosidad

## Resumen
Los datos de **Cartera**, **Cobrado** y **Morosidad** en los gráficos del dashboard **NO son acumulativos** y corresponden **SOLO a cada mes/día de forma independiente**.

---

## Definiciones Correctas

### 1. CARTERA (Pagos Programados)
**Cuotas vencidas (con vencimiento) en ese período**, sin importar si fueron pagadas.

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
- **Cartera Febrero = Cuota 1 + Cuota 2**

---

### 2. COBRADO (Pagos Conciliados)
**Cuotas que fueron PAGADAS en ese período** (sin importar cuándo vencieron).

```sql
SELECT SUM(monto) 
FROM cuotas 
WHERE fecha_pago BETWEEN inicio_mes AND fin_mes
  AND fecha_pago IS NOT NULL
  AND prestamo.estado = 'APROBADO';
```

**Ejemplo mes Febrero 2026:**
- Cuota 1: Vence 2026-02-05, Pago: NULL → **NO incluida** en Cobrado
- Cuota 2: Vence 2026-02-10, Pago: 2026-02-15 → Incluida en Cobrado
- Cuota 3: Vence 2026-01-15, Pago: 2026-02-05 → Incluida en Cobrado (se pagó en febrero)
- **Cobrado Febrero = Cuota 2 + Cuota 3**

---

### 3. MOROSIDAD (Pago Vencido)
**Cuotas que VENCIERON en ese período Y AÚN NO FUERON PAGADAS** (y su vencimiento está en el pasado).

```sql
SELECT SUM(monto) 
FROM cuotas 
WHERE fecha_vencimiento BETWEEN inicio_mes AND fin_mes
  AND fecha_vencimiento < HOY
  AND fecha_pago IS NULL
  AND prestamo.estado = 'APROBADO';
```

**Ejemplo mes Febrero 2026 (verificación el 2026-02-28):**
- Cuota 1: Vence 2026-02-05, Pago: NULL → Incluida en Morosidad (pasó su vencimiento)
- Cuota 2: Vence 2026-02-10, Pago: 2026-02-15 → **NO incluida** (fue pagada)
- Cuota 3: Vence 2026-01-15, Pago: 2026-02-05 → **NO incluida** (vence en enero, no en febrero)
- Cuota 4: Vence 2026-03-01, Pago: NULL → **NO incluida** (aún no venció en febrero 28)
- **Morosidad Febrero = Cuota 1 solamente**

---

## Relación entre métricas

### ❌ INCORRECTO: Morosidad = Cartera - Cobrado
Esta fórmula es **FALSA** porque mezcla períodos de vencimiento con períodos de pago.

**Contraejemplo:**
| | Cartera Feb | Cobrado Feb | Fórmula (Cartera - Cobrado) | Morosidad Real |
|---|---|---|---|---|
| **Mes Febrero** | $100 | $120 | -$20 ❌ | $30 ✅ |

**Explicación:**
- Cartera Febrero = $100 (cuotas vencidas en febrero)
- Cobrado Febrero = $120 (cuotas pagadas en febrero, incluyendo $20 de enero y $100 de febrero)
- La fórmula da -$20 (negativo, absurdo)
- La Morosidad Real = $30 (cuotas de febrero que siguen sin pagar: $100 - $70 que se pagaron después)

---

## Verificación de Coherencia

Para cada mes, se debe cumplir:

1. **Cartera ≥ 0** (siempre es suma de montos positivos)
2. **Cobrado ≥ 0** (siempre es suma de montos positivos)
3. **Morosidad ≥ 0** (siempre es suma de montos positivos)
4. **Morosidad ≤ Cartera** (nunca hay más vencido que programado)
5. **Cobrado puede ser > Cartera** (si se pagan cuotas atrasadas de meses anteriores)

**Ejemplo coherente:**
```
Febrero 2026:
- Cartera:   $1,500 (cuotas con vencimiento en feb)
- Cobrado:   $1,800 (cuotas pagadas en feb, incluyendo atrasos de enero)
- Morosidad: $  200 (cuotas de feb aún sin pagar)

Validación:
✅ Todos ≥ 0
✅ Morosidad ($200) ≤ Cartera ($1,500)
✅ Cobrado ($1,800) > Cartera ($1,500) → OK, son pagos de atrasados
```

---

## Impacto en el Dashboard

### Gráfico "Evolución Mensual" (Cartera, Cobrado, Morosidad)
- **Eje X**: Meses (Abr 2025, May 2025, ..., Mar 2026)
- **Eje Y (barras azules)**: Cartera de ese mes
- **Eje Y (barras verdes)**: Cobrado en ese mes
- **Eje Y (línea roja)**: Morosidad de ese mes

**Interpretación correcta:**
> "En Febrero 2026, se programó cobrar $1,500 (barrita azul). Se cobraron $1,800 (barrita verde, incluyendo pagos atrasados). De los $1,500 programados, $200 aún están vencidos (línea roja)."

**Interpretación INCORRECTA:**
> "La diferencia entre las barras ($1,800 - $1,500 = $300) es la morosidad." ❌

---

## Implementación en Backend

El cálculo está en `backend/app/api/v1/endpoints/dashboard/kpis.py`, función `_compute_dashboard_admin()`:

```python
# CARTERA: Cuotas programadas en este mes
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

# COBRADO: Cuotas pagadas en este mes
cobrado = db.scalar(
    select(func.coalesce(func.sum(Cuota.monto), 0))
    .select_from(Cuota)
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .where(
        Prestamo.estado == "APROBADO",
        Cuota.fecha_pago >= inicio_d,
        Cuota.fecha_pago <= fin_d,
        Cuota.fecha_pago.isnot(None),
    )
) or 0

# MOROSIDAD: Cuotas vencidas en este mes sin pagar
morosidad = db.scalar(
    select(func.coalesce(func.sum(Cuota.monto), 0))
    .select_from(Cuota)
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .where(
        Prestamo.estado == "APROBADO",
        Cuota.fecha_vencimiento >= inicio_d,
        Cuota.fecha_vencimiento <= fin_d,
        Cuota.fecha_vencimiento < HOY,
        Cuota.fecha_pago.is_(None),
    )
) or 0
```

---

## Conclusión

✅ **Cada mes es independiente**  
✅ **No hay acumulación entre períodos**  
✅ **Cartera, Cobrado y Morosidad son métricas independientes**  
✅ **Morosidad ≠ Cartera - Cobrado**
