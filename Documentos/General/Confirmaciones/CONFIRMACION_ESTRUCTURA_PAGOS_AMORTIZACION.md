# ✅ Confirmación: Estructura de Pagos basada en Tabla de Amortización

## 🔄 FLUJO COMPLETO: GENERACIÓN Y APLICACIÓN DE PAGOS

### 📊 1. GENERACIÓN DE TABLA DE AMORTIZACIÓN

**Ubicación:** `backend/app/services/prestamo_amortizacion_service.py`

#### ✅ Proceso de Generación:
```python
def generar_tabla_amortizacion(prestamo: Prestamo, fecha_base: date, db: Session):
    # 1. Elimina cuotas existentes si las hay
    db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).delete()

    # 2. Calcula cada cuota según:
    #    - monto_cuota (ej: $140.00)
    #    - monto_capital (parte de capital de la cuota)
    #    - monto_interes (parte de interés de la cuota)
    #    - fecha_vencimiento (fecha límite de pago)

    # 3. Inicializa cada cuota con:
    cuota = Cuota(
        prestamo_id=prestamo.id,
        numero_cuota=numero_cuota,  # 1, 2, 3, ...
        fecha_vencimiento=fecha_vencimiento,
        monto_cuota=monto_cuota,      # ✅ MONTO TOTAL DE LA CUOTA ($140)
        monto_capital=monto_capital,
        monto_interes=monto_interes,
        capital_pagado=Decimal("0.00"),      # ✅ INICIA EN 0
        interes_pagado=Decimal("0.00"),       # ✅ INICIA EN 0
        total_pagado=Decimal("0.00"),         # ✅ INICIA EN 0
        capital_pendiente=monto_capital,      # ✅ INICIA CON TODO EL CAPITAL
        interes_pendiente=monto_interes,      # ✅ INICIA CON TODO EL INTERÉS
        estado="PENDIENTE"                    # ✅ ESTADO INICIAL
    )
```

**Cuándo se genera:**
- ✅ Cuando un préstamo pasa a estado "APROBADO"
- ✅ Cuando se ejecuta manualmente el endpoint `/prestamos/{id}/generar-amortizacion`
- ✅ Se guarda en la tabla `cuotas` de la base de datos

---

### 💰 2. REGISTRO DE PAGO

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` - `crear_pago()`

#### ✅ Datos del Pago:
```python
pago = Pago(
    cedula_cliente="E1803113360",
    prestamo_id=1,                    # ✅ VINCULADO AL PRÉSTAMO
    monto_pagado=40.00,               # ✅ MONTO DEL PAGO (puede ser parcial)
    fecha_pago="2025-10-29",
    numero_documento="ASS3545213521",
    estado="PAGADO"
)
```

**Después de crear el pago:**
```python
# ✅ AUTOMÁTICAMENTE se llama:
aplicar_pago_a_cuotas(nuevo_pago, db, current_user)
```

---

### 🔄 3. APLICACIÓN DE PAGO A CUOTAS (MECANISMO DE VERIFICACIÓN)

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` - `aplicar_pago_a_cuotas()`

#### ✅ PROCESO DE VERIFICACIÓN Y APLICACIÓN:

```python
def aplicar_pago_a_cuotas(pago: Pago, db: Session, current_user: User):
    # ✅ PASO 1: Buscar cuotas de la tabla de amortización
    cuotas = db.query(Cuota).filter(
        Cuota.prestamo_id == pago.prestamo_id,    # ✅ VERIFICA préstamo_id
        Cuota.estado != "PAGADO"                  # ✅ Solo cuotas pendientes
    ).order_by(Cuota.numero_cuota).all()          # ✅ Orden secuencial

    saldo_restante = pago.monto_pagado

    for cuota in cuotas:  # ✅ ITERA sobre cada cuota de la amortización
        # ✅ PASO 2: Calcular cuánto falta para completar la cuota
        monto_faltante = cuota.monto_cuota - cuota.total_pagado

        # ✅ PASO 3: Aplicar solo lo necesario (o el saldo disponible)
        monto_aplicar = min(saldo_restante, monto_faltante)

        # ✅ PASO 4: Actualizar campos de la CUOTA en la tabla de amortización
        cuota.capital_pagado += capital_aplicar      # ✅ INCREMENTA lo pagado
        cuota.interes_pagado += interes_aplicar
        cuota.total_pagado += monto_aplicar
        cuota.capital_pendiente -= capital_aplicar   # ✅ DISMINUYE lo pendiente
        cuota.interes_pendiente -= interes_aplicar

        # ✅ PASO 5: Verificar estado según regla de negocio
        if cuota.total_pagado >= cuota.monto_cuota:  # ✅ COMPARACIÓN CON monto_cuota
            cuota.estado = "PAGADO"
        elif cuota.total_pagado > 0:
            # Estado ATRASADO si vencida, PENDIENTE si no
            cuota.estado = "ATRASADO" if vencida else "PENDIENTE"

        saldo_restante -= monto_aplicar
```

---

## 🔍 MECANISMO DE VERIFICACIÓN

### ✅ CONFIRMACIÓN: La estructura de pagos SÍ se basa en la tabla de amortización

| Aspecto | Confirmación |
|---------|--------------|
| **Tabla de Referencia** | ✅ Las cuotas de la tabla `cuotas` (amortización) son la FUENTE DE VERDAD |
| **Vinculación** | ✅ Pagos se vinculan al `prestamo_id` → Busca cuotas de ese préstamo |
| **Aplicación Secuencial** | ✅ Pagos se aplican a cuotas en orden (`numero_cuota` 1, 2, 3...) |
| **Verificación de Monto** | ✅ Compara `total_pagado` vs `monto_cuota` de cada cuota |
| **Rastreo de Estado** | ✅ Estado de cada cuota se actualiza según pagos recibidos |
| **Validación de Completitud** | ✅ Solo marca "PAGADO" cuando `total_pagado >= monto_cuota` |

---

## 📋 EJEMPLO PRÁCTICO

### Escenario: Préstamo con 3 cuotas de $140 cada una

#### **1. Generación de Amortización:**
```sql
INSERT INTO cuotas (prestamo_id, numero_cuota, monto_cuota, total_pagado, estado) VALUES
(1, 1, 140.00, 0.00, 'PENDIENTE'),
(1, 2, 140.00, 0.00, 'PENDIENTE'),
(1, 3, 140.00, 0.00, 'PENDIENTE');
```

#### **2. Registro de Pago Parcial ($40):**
```sql
INSERT INTO pagos (prestamo_id, monto_pagado) VALUES (1, 40.00);
```

#### **3. Aplicación Automática:**
```python
# ✅ Busca cuotas del préstamo 1:
cuotas = [cuota_1, cuota_2, cuota_3]

# ✅ Aplica a primera cuota:
cuota_1.total_pagado = 0 + 40 = 40
cuota_1.estado = "ATRASADO"  # Porque 40 < 140
```

#### **4. Registro de Segundo Pago ($100):**
```python
# ✅ Busca cuotas pendientes del préstamo 1:
cuotas = [cuota_1, cuota_2, cuota_3]  # cuota_1 aún no está PAGADO

# ✅ Aplica a primera cuota:
cuota_1.total_pagado = 40 + 100 = 140  # ✅ COMPLETO
cuota_1.estado = "PAGADO"  # Porque 140 >= 140

# ✅ NO hay saldo restante, proceso termina
```

#### **5. Resultado en la Tabla de Amortización:**
```sql
SELECT numero_cuota, monto_cuota, total_pagado, estado FROM cuotas WHERE prestamo_id = 1;

-- Resultado:
-- 1 | 140.00 | 140.00 | PAGADO    ✅
-- 2 | 140.00 |   0.00 | PENDIENTE
-- 3 | 140.00 |   0.00 | PENDIENTE
```

---

## ✅ RESUMEN DE CONFIRMACIÓN

### **La estructura de pagos SÍ se basa en la tabla de amortización:**

1. ✅ **Tabla `cuotas` es la fuente de verdad**
   - Contiene el `monto_cuota` esperado ($140)
   - Rastrea `total_pagado` acumulado
   - Mantiene `estado` actualizado

2. ✅ **Pagos se vinculan al `prestamo_id`**
   - `pago.prestamo_id` → Busca todas las cuotas de ese préstamo
   - No se vincula a una cuota específica, sino que se aplica secuencialmente

3. ✅ **Mecanismo de verificación:**
   ```python
   # Para cada pago:
   # 1. Busca cuotas de la amortización: Cuota.prestamo_id == pago.prestamo_id
   # 2. Itera secuencialmente: order_by(Cuota.numero_cuota)
   # 3. Verifica cuánto falta: monto_faltante = monto_cuota - total_pagado
   # 4. Aplica solo lo necesario: min(saldo_restante, monto_faltante)
   # 5. Actualiza campos de la cuota: total_pagado += monto_aplicar
   # 6. Verifica completitud: total_pagado >= monto_cuota → "PAGADO"
   ```

4. ✅ **Rastreo completo:**
   - Cada pago actualiza `total_pagado`, `capital_pagado`, `interes_pagado`
   - Disminuye `capital_pendiente` e `interes_pendiente`
   - Actualiza `estado` según regla de negocio

---

## 🔐 GARANTÍAS DEL SISTEMA

1. ✅ **Integridad:** Los pagos solo se aplican a cuotas existentes en la amortización
2. ✅ **Secuencialidad:** Se aplican cuota por cuota, en orden
3. ✅ **Completitud:** Solo marca "PAGADO" cuando `total_pagado >= monto_cuota`
4. ✅ **Rastreabilidad:** Cada cambio se refleja en los campos de la tabla `cuotas`
5. ✅ **Consistencia:** La tabla de amortización siempre refleja el estado real de pagos

---

## ✅ CONCLUSIÓN

**SÍ, confirmado:** La estructura de pagos **SE BASA COMPLETAMENTE** en la tabla de amortización generada como mecanismo de verificación de pagos y abonos. La tabla `cuotas` es la **FUENTE DE VERDAD** para:

- ✅ Determinar cuánto se debe por cuota (`monto_cuota`)
- ✅ Rastrear cuánto se ha pagado (`total_pagado`)
- ✅ Verificar si una cuota está completa (`total_pagado >= monto_cuota`)
- ✅ Mantener el estado actualizado de cada cuota
- ✅ Aplicar pagos parciales secuencialmente

La tabla `pagos` registra los **eventos de pago**, pero la **verificación y aplicación** se hace contra la **tabla de amortización (`cuotas`)**.

