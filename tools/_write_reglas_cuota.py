# -*- coding: utf-8 -*-
from pathlib import Path

CONTENT = """# Reglas de negocio - Estados de cuota

Documento alineado con la **tabla de amortizacion** en el modal **Detalles del Prestamo** (columna **Estado**) y con la implementacion en `backend/app/services/cuota_estado.py` (**America/Caracas**).

---

## Pantalla de referencia (modal prestamo)

En **Tabla de Amortizacion** del detalle del prestamo se muestran, entre otras:

| Columna            | Significado |
|--------------------|-------------|
| Cuota              | Numero de cuota |
| Fecha vencimiento  | Fecha de vencimiento contractual |
| Capital / Interes / Total | Componentes de la cuota (en producto actual el interes puede ser 0) |
| Saldo pendiente    | Saldo del prestamo despues de esa fila (capital restante del calendario) |
| **Pago conciliado**| Monto **conciliado** en banco (referencia contable). **No sustituye** el estado de cobranza de la columna **Estado**. |
| **Estado**         | Estado de cobranza segun reglas de esta seccion (badges: Pendiente, Vencido (1-91 d), Mora (92+ d), Pagado, Pago adelantado, Pendiente parcial) |
| Recibo             | Descarga de recibo cuando aplica |

La columna **Estado** se calcula con **total pagado aplicado a la cuota** (`total_pagado` desde `cuota_pagos` / modelo) y **fecha de vencimiento**, no solo con el monto conciliado. En el frontend, el respaldo usa el mayor entre `total_pagado` y `pago_monto_conciliado` solo si el estado del backend no es confiable.

---

## Definiciones (fuente unica: `cuota_estado.py`)

**Fecha de referencia ("hoy"):** calendario en **America/Caracas**.

**Tolerancia de monto:** cuota cubierta al 100% si `total_pagado >= monto_cuota - 0.01`.

### 1. PAGADO

- Cuota cubierta al 100% y **fecha de vencimiento <= hoy** (vencida o hoy).

### 2. PAGO_ADELANTADO

- Cuota cubierta al 100% y **fecha de vencimiento > hoy**.

**Etiqueta en UI:** "Pago adelantado".

### 3. PENDIENTE

- No cubierta al 100%, **sin retraso**: el **dia del vencimiento cuenta como al corriente** (`dias de retraso = 0`).

### 4. PARCIAL

- No cubierta al 100%, sin retraso (mismo dia de vencimiento o futuro), con abonos (`paid > 0.001`).

**Etiqueta en UI:** "Pendiente parcial".

### 5. VENCIDO

- No cubierta al 100%, con **1 a 91 dias calendario** de retraso desde el vencimiento (el dia siguiente al vencimiento = 1 dia de retraso).

**Etiqueta en UI:** `Vencido (1-91 d)`.

> Nota: En documentos antiguos se usaba el termino "VENCIDA"; en sistema y UI unificado se usa **VENCIDO**.

### 6. MORA

- No cubierta al 100%, con **92 o mas dias calendario** de retraso desde el vencimiento.

**Etiqueta en UI:** `Mora (92+ d)`.

---

## Calculo de dias de retraso

    dias_retraso = max(0, (hoy_Caracas - fecha_vencimiento).days)

- `dias_retraso == 0`: incluye el **dia del vencimiento** -> al corriente para fines de estado (Pendiente / Parcial).
- `1 <= dias_retraso <= 91` -> **VENCIDO**.
- `dias_retraso >= 92` -> **MORA**.

---

## Ejemplo alineado con tabla (cuota USD 260, vencimientos mensuales)

Si **hoy** (Caracas) esta **despues del 13/03/2026** y **antes del 13/04/2026**:

| Cuota | Vencimiento | Pagado | Estado esperado |
|-------|-------------|--------|-----------------|
| 1 | 13/01/2026 | 260 | **Pagado** |
| 2 | 13/02/2026 | 0 | **Vencido (1-91 d)** |
| 3 | 13/03/2026 | 0 | **Vencido (1-91 d)** |
| 4 | 13/04/2026 | 0 | **Pendiente** |
| 5 | 13/05/2026 | 0 | **Pendiente** |

---

## Matriz de transiciones (referencia)

Los cambios reales los gobiernan aplicacion de pagos y reglas en `pagos.py` / servicios; esta matriz resume intencion operativa:

| De / A        | PENDIENTE | PARCIAL | VENCIDO | MORA | PAGADO | PAGO_ADELANTADO |
|---------------|-----------|---------|---------|------|--------|-----------------|
| PENDIENTE     | si        | si      | si      | si   | si     | si              |
| PARCIAL       | si        | si      | si      | si   | si     | si              |
| VENCIDO       | no*       | si      | si      | si   | si     | si              |
| MORA          | no*       | si      | no      | si   | si     | si              |
| PAGADO        | no        | no      | no      | no   | si     | no              |
| PAGO_ADELANTADO | no      | no      | no      | no   | si     | si              |

* No se vuelve "pendiente" sin corregir fechas o datos; el estado se recalcula segun hoy y pagos.

---

## Archivos que implementan la logica

### Backend

1. **`backend/app/services/cuota_estado.py`** (fuente unica de verdad en Python)
   - `hoy_negocio()`, `clasificar_estado_cuota()`, `estado_cuota_para_mostrar()`, `dias_retraso_desde_vencimiento()`
   - Constantes SQL: `SQL_PG_ESTADO_CUOTA_CASE_CORRELATED`, `SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE`

2. **`backend/app/api/v1/endpoints/prestamos.py`** - armado de cuotas / amortizacion para API y exportes

3. **`backend/app/api/v1/endpoints/pagos.py`** - aplicacion de pagos y transiciones

4. **`backend/app/services/conciliacion_automatica_service.py`** - actualizacion de estado alineada al clasificador

5. **PDF / estado de cuenta / notificaciones** - usan `estado_cuota_para_mostrar` o equivalente con Caracas donde aplica

### Frontend

6. **`frontend/src/components/prestamos/TablaAmortizacionPrestamo.tsx`**
   - Badges y etiquetas: Pendiente, Pagado, Vencido (1-91 d), Mora (92+ d), Pago adelantado, Pendiente parcial
   - Respaldo local con `hoyCaracas()` si el `estado` de la API no es uno de la lista confiable

---

## Conciliacion bancaria vs columna Estado

- **Pago conciliado** en pantalla informa el monto reconocido en conciliacion.
- **Estado** refleja la situacion frente al cliente y al calendario (**cobranza**), derivada de montos aplicados a la cuota y vencimiento.
- El valor **CONCILIADO** no se usa como etiqueta de estado en esta columna.

---

## Preguntas frecuentes

**P: Si la cuota vence hoy y no hay pago, cual es el estado?**  
A: **Pendiente** (el dia del vencimiento es al corriente).

**P: A partir de cuando es Vencido?**  
A: Desde el **dia calendario siguiente** al vencimiento, hasta 91 dias de retraso.

**P: Cuando pasa a Mora?**  
A: Con **92 o mas dias** de retraso desde el vencimiento y cuota no cubierta al 100%.

**P: Interesa el huso horario del servidor?**  
A: No para esta regla: **hoy** de negocio es **America/Caracas** en el codigo unificado.

---

## Historial de cambios

| Fecha      | Cambio |
|------------|--------|
| 20/03/2026 | Documentacion inicial |
| 21/03/2026 | Alineacion con UI modal amortizacion, VENCIDO 1-91 / MORA 92+, Caracas, columnas, PAGO_ADELANTADO y PARCIAL |

"""

Path(__file__).resolve().parents[1].joinpath(
    "REGLAS_NEGOCIO_ESTADOS_CUOTA.md"
).write_text(CONTENT, encoding="utf-8")
print("ok")
