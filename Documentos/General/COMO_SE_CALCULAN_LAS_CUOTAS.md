# CÓMO SE CALCULAN LAS CUOTAS POR CADA PRÉSTAMO

## 📋 RESUMEN

Las cuotas se calculan usando el **Método Francés (cuota fija)** cuando un préstamo se aprueba. El cálculo se realiza en el servicio `prestamo_amortizacion_service.py`.

---

## 🔧 PROCESO DE CÁLCULO

### 1. **Ubicación del Código**

**Archivo:** `backend/app/services/prestamo_amortizacion_service.py`

**Función principal:**
```python
def generar_tabla_amortizacion(prestamo: Prestamo, fecha_base: date, db: Session) -> List[Cuota]
```

---

### 2. **Datos Requeridos del Préstamo**

Para calcular las cuotas, se necesitan estos datos del préstamo:

- ✅ `total_financiamiento`: Monto total del préstamo
- ✅ `numero_cuotas`: Número de cuotas planificadas
- ✅ `cuota_periodo`: Monto fijo de cada cuota (`total_financiamiento / numero_cuotas`)
- ✅ `modalidad_pago`: MENSUAL, QUINCENAL o SEMANAL
- ✅ `tasa_interes`: Tasa de interés anual (%)
- ✅ `fecha_base_calculo`: Fecha desde la cual se calculan las fechas de vencimiento

---

### 3. **Cálculo del Número de Cuotas**

**Función:** `calcular_cuotas()` en `prestamos.py`

**Lógica:**

```python
# Si hay plazo_maximo_meses (después de evaluación de riesgo):
- MENSUAL: plazo_maximo_meses cuotas
- QUINCENAL: plazo_maximo_meses * 2 cuotas
- SEMANAL: plazo_maximo_meses * 4 cuotas

# Si NO hay plazo_maximo (DRAFT, antes de evaluación):
- MENSUAL: 36 cuotas (por defecto)
- QUINCENAL: 72 cuotas (36 * 2)
- SEMANAL: 144 cuotas (36 * 4)

# Monto de cada cuota:
cuota_periodo = total_financiamiento / numero_cuotas
```

**Ejemplo:**
- Préstamo: $10,000
- Modalidad: MENSUAL
- Plazo máximo: 12 meses
- **Resultado:** 12 cuotas de $833.33 cada una

---

### 4. **Proceso de Generación de Cuotas**

#### Paso 1: Validación
```python
- total_financiamiento > 0
- numero_cuotas > 0
```

#### Paso 2: Eliminar cuotas existentes (si las hay)
```python
db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).delete()
```

#### Paso 3: Calcular intervalo entre cuotas
```python
intervalos = {
    "MENSUAL": 30 días (usa relativedelta para meses calendario)
    "QUINCENAL": 15 días
    "SEMANAL": 7 días
}
```

#### Paso 4: Calcular tasa de interés mensual
```python
if tasa_interes == 0:
    tasa_mensual = 0
else:
    tasa_mensual = tasa_interes / 100 / 12
```

**Ejemplo:**
- Tasa anual: 12%
- Tasa mensual: 12 / 100 / 12 = 0.01 (1% mensual)

#### Paso 5: Generar cada cuota (loop de 1 a numero_cuotas)

Para cada cuota `numero_cuota` (1, 2, 3, ..., numero_cuotas):

**a) Calcular fecha de vencimiento:**
```python
if modalidad == "MENSUAL":
    fecha_vencimiento = fecha_base + relativedelta(months=numero_cuota)
    # Ejemplo: fecha_base = 2025-01-15, cuota 1 → 2025-02-15
else:
    fecha_vencimiento = fecha_base + timedelta(days=intervalo_dias * numero_cuota)
    # QUINCENAL: +15 días por cuota
    # SEMANAL: +7 días por cuota
```

**b) Monto de la cuota (Método Francés - cuota fija):**
```python
monto_cuota = prestamo.cuota_periodo  # Valor fijo para todas las cuotas
```

**c) Calcular interés sobre saldo pendiente:**
```python
if tasa_mensual == 0:
    monto_interes = 0
    monto_capital = monto_cuota
else:
    monto_interes = saldo_capital * tasa_mensual
    monto_capital = monto_cuota - monto_interes
```

**d) Actualizar saldo de capital:**
```python
saldo_capital_inicial = saldo_capital  # Saldo antes de esta cuota
saldo_capital = saldo_capital - monto_capital  # Reducir capital
saldo_capital_final = saldo_capital  # Saldo después de esta cuota
```

**e) Crear registro de cuota:**
```python
Cuota(
    prestamo_id=prestamo.id,
    numero_cuota=numero_cuota,  # 1, 2, 3, ...
    fecha_vencimiento=fecha_vencimiento,
    monto_cuota=monto_cuota,  # Valor fijo
    monto_capital=monto_capital,  # Varía según saldo
    monto_interes=monto_interes,  # Varía según saldo
    saldo_capital_inicial=saldo_capital_inicial,
    saldo_capital_final=saldo_capital_final,
    capital_pagado=0.00,  # Inicia en 0
    interes_pagado=0.00,  # Inicia en 0
    total_pagado=0.00,  # Inicia en 0
    capital_pendiente=monto_capital,
    interes_pendiente=monto_interes,
    estado="PENDIENTE"
)
```

---

## 📊 EJEMPLO DE CÁLCULO

### Préstamo de Ejemplo:
- **Total financiamiento:** $10,000
- **Número de cuotas:** 12
- **Modalidad:** MENSUAL
- **Tasa de interés:** 12% anual (1% mensual)
- **Fecha base:** 2025-01-15
- **Cuota fija:** $833.33 ($10,000 / 12)

### Cálculo de las primeras 3 cuotas:

#### Cuota 1:
```
Saldo inicial: $10,000.00
Fecha vencimiento: 2025-02-15
Monto cuota: $833.33
Interés: $10,000.00 * 0.01 = $100.00
Capital: $833.33 - $100.00 = $733.33
Saldo final: $10,000.00 - $733.33 = $9,266.67
```

#### Cuota 2:
```
Saldo inicial: $9,266.67
Fecha vencimiento: 2025-03-15
Monto cuota: $833.33
Interés: $9,266.67 * 0.01 = $92.67
Capital: $833.33 - $92.67 = $740.66
Saldo final: $9,266.67 - $740.66 = $8,526.01
```

#### Cuota 3:
```
Saldo inicial: $8,526.01
Fecha vencimiento: 2025-04-15
Monto cuota: $833.33
Interés: $8,526.01 * 0.01 = $85.26
Capital: $833.33 - $85.26 = $748.07
Saldo final: $8,526.01 - $748.07 = $7,777.94
```

**Observación:** 
- ✅ El monto de la cuota es **FIJO** ($833.33)
- ✅ El interés **DISMINUYE** en cada cuota (porque el saldo disminuye)
- ✅ El capital **AUMENTA** en cada cuota (porque interés disminuye)
- ✅ El saldo de capital **DISMINUYE** progresivamente

---

## 🔄 MÉTODO FRANCÉS (CUOTA FIJA)

### Características:
1. **Cuota constante:** Todas las cuotas tienen el mismo monto (`cuota_periodo`)
2. **Interés decreciente:** El interés se calcula sobre el saldo pendiente, que disminuye
3. **Capital creciente:** Como la cuota es fija y el interés disminuye, el capital aumenta
4. **Saldo decreciente:** El saldo de capital se reduce progresivamente

### Fórmulas:

```
monto_cuota = total_financiamiento / numero_cuotas  (FIJO)

Para cada cuota:
  monto_interes = saldo_capital * tasa_mensual
  monto_capital = monto_cuota - monto_interes
  saldo_capital = saldo_capital - monto_capital
```

---

## 📅 CÁLCULO DE FECHAS DE VENCIMIENTO

### MENSUAL:
```python
fecha_vencimiento = fecha_base + relativedelta(months=numero_cuota)
```
- Usa `relativedelta` para mantener el mismo día del mes
- Ejemplo: Si fecha_base es día 15, todas las cuotas vencen el día 15
- Ajusta automáticamente si el día no existe (ej: día 31 en febrero → último día de febrero)

### QUINCENAL:
```python
fecha_vencimiento = fecha_base + timedelta(days=15 * numero_cuota)
```
- Suma 15 días por cada cuota

### SEMANAL:
```python
fecha_vencimiento = fecha_base + timedelta(days=7 * numero_cuota)
```
- Suma 7 días por cada cuota

---

## ⚙️ CUÁNDO SE GENERAN LAS CUOTAS

Las cuotas se generan automáticamente cuando:

1. **Un préstamo pasa a estado APROBADO**
   - Se ejecuta `generar_tabla_amortizacion()` automáticamente
   - Requiere que el préstamo tenga `fecha_base_calculo`

2. **Manualmente vía API:**
   ```
   POST /api/v1/prestamos/{prestamo_id}/generar-amortizacion
   ```

3. **Scripts masivos:**
   - `scripts/python/Generar_Cuotas_Masivas.py`
   - `scripts/python/Generar_Amortizacion_Prestamos_Faltantes.py`

---

## ✅ VALIDACIONES POST-GENERACIÓN

Después de generar todas las cuotas, el sistema valida:

```python
total_calculado = sum(c.monto_cuota for c in cuotas_generadas)
diferencia = abs(total_calculado - prestamo.total_financiamiento)

if diferencia > 0.01:  # Tolerancia de 1 centavo
    logger.warning("Diferencia en total de cuotas")
```

**Nota:** En el método francés, la suma de todas las cuotas puede no ser exactamente igual al `total_financiamiento` debido a los intereses. La validación verifica que la diferencia sea mínima.

---

## 📝 RESUMEN DEL PROCESO

1. ✅ **Calcular número de cuotas** según modalidad y plazo máximo
2. ✅ **Calcular monto de cuota** (`total_financiamiento / numero_cuotas`)
3. ✅ **Eliminar cuotas existentes** (si las hay)
4. ✅ **Para cada cuota (1 a numero_cuotas):**
   - Calcular fecha de vencimiento
   - Calcular interés sobre saldo pendiente
   - Calcular capital (cuota - interés)
   - Actualizar saldo de capital
   - Crear registro de cuota
5. ✅ **Guardar todas las cuotas** en la base de datos
6. ✅ **Validar consistencia** de la tabla generada

---

## 🎯 RESULTADO

Al finalizar, cada préstamo aprobado tiene:
- ✅ `numero_cuotas` registros en la tabla `cuotas`
- ✅ Cada cuota con `numero_cuota` único (1, 2, 3, ..., numero_cuotas)
- ✅ Fechas de vencimiento calculadas según modalidad
- ✅ Montos de capital e interés calculados según método francés
- ✅ Saldos de capital actualizados progresivamente
