# Análisis integral: Trazabilidad Pago → Cliente → Préstamo → Cuota

## Objetivo del caso

Cuando se carga un pago en la tabla **pagos** con referencia **cédula**, se requiere:

1. **Trazabilidad**: poder seguir la cadena y verificar que el préstamo y el cliente tienen una **única y solvente** conexión.
2. **Una sola línea de conexión**: garantizar que existe una única cadena consistente **Cliente → Préstamo → Cuota → Pago** (y tabla de detalle **cuota_pagos**).

Este documento analiza el modelo actual, los puntos de quiebre y propone criterios y mecanismos para verificar esa línea única y solvente.

---

## 1. Modelo de datos actual: la cadena de conexión

### 1.1 Esquema conceptual

```
Cliente (clientes)
   │
   │ cliente_id
   ▼
Préstamo (prestamos)  ◄──── prestamo_id ────  Pago (pagos)
   │                          │
   │ prestamo_id              │ cedula_cliente (referencia cédula)
   ▼                          │
Cuota (cuotas)  ──────────────┘
   │
   │ cuota_id + pago_id
   ▼
CuotaPago (cuota_pagos)  ← detalle: qué monto del pago se aplicó a cada cuota
```

### 1.2 Tablas y relaciones (BD)

| Tabla        | Clave / FK relevante        | Relación con la cadena |
|-------------|-----------------------------|--------------------------|
| **clientes** | `id`, `cedula`              | Origen: un cliente se identifica por `cedula`. |
| **prestamos** | `id`, `cliente_id` (FK → clientes.id), `cedula` (denormalizado) | Un préstamo pertenece a un cliente. |
| **cuotas**   | `id`, `prestamo_id` (FK → prestamos.id), `pago_id` (nullable, FK → pagos.id) | Cada cuota pertenece a un préstamo; opcionalmente se asocia un pago (legacy/último). |
| **pagos**    | `id`, `cedula_cliente` (columna `cedula` en BD), `prestamo_id` (nullable, FK → prestamos.id) | El pago se carga con **referencia cédula**; puede tener **prestamo_id** asignado (manual o automático). |
| **cuota_pagos** | `cuota_id`, `pago_id`, `monto_aplicado` | Detalle: qué parte del pago se aplicó a cada cuota (trazabilidad pago ↔ cuota). |

En la BD existe (o existió) restricción **fk_pagos_cedula**: `pagos.cedula` debe existir en `clientes.cedula`, de modo que la referencia por cédula obliga a que el cliente exista.

### 1.3 Dónde se usa la “referencia cédula” al cargar un pago

- **Carga masiva (Excel)**: se envía cédula (y opcionalmente crédito/prestamo_id). Si no se envía préstamo y la cédula tiene **un solo crédito activo** (APROBADO/DESEMBOLSADO), el backend asigna `prestamo_id` automáticamente.
- **Crear pago (POST)**: se envía `cedula_cliente` y opcionalmente `prestamo_id`. Si se envía `prestamo_id`, el pago queda ligado a ese préstamo.
- **Conciliación**: se marcan pagos por `numero_documento` y se les asigna préstamo cuando aplica; luego se aplica el pago a cuotas (FIFO) de ese préstamo.

La “referencia cédula” en el pago es, por tanto, **pagos.cedula_cliente** (columna `cedula` en BD).

---

## 2. Qué significa “única y solvente” conexión

### 2.1 Una sola línea de conexión

- **Cliente**: existe **un** cliente con `clientes.cedula = pagos.cedula_cliente`.
- **Préstamo**: si el pago tiene `prestamo_id`, debe existir **un** préstamo con `prestamos.id = pagos.prestamo_id` y `prestamos.cliente_id = cliente.id` (y normalmente `prestamos.cedula = pagos.cedula_cliente`).
- **Cuotas**: las cuotas afectadas por ese pago son **solo** las del mismo préstamo (`cuotas.prestamo_id = pagos.prestamo_id`), y el detalle está en **cuota_pagos** (pago_id + cuota_id + monto_aplicado).

Es decir: **una sola línea** = un único cliente para esa cédula, un único préstamo asociado al pago (cuando existe prestamo_id), y las cuotas/cuota_pagos alineadas con ese préstamo y ese pago.

### 2.2 Conexión “solvente” (consistente)

- **Cédula coherente**: `pagos.cedula_cliente` = `clientes.cedula` del cliente al que pertenece el préstamo = `prestamos.cedula` (cuando está denormalizado).
- **Préstamo del mismo cliente**: `prestamos.cliente_id` = `clientes.id` del cliente con esa cédula.
- **Aplicación a cuotas correcta**: las filas en `cuota_pagos` para ese `pago_id` tienen `cuota_id` en cuotas con `prestamo_id = pagos.prestamo_id`, y la suma de `monto_aplicado` no supera `pagos.monto_pagado`.

Cualquier desvío (pago con cédula que no existe en clientes, prestamo_id de otro cliente, o cuota_pagos apuntando a cuotas de otro préstamo) rompe la “solvencia” de la cadena.

---

## 3. Puntos donde la cadena puede romperse

| Riesgo | Descripción | Mitigación actual |
|--------|-------------|-------------------|
| Pago sin cliente | `pagos.cedula_cliente` no existe en `clientes.cedula` | FK `fk_pagos_cedula` (si está activa) impide insertar. |
| Pago sin préstamo | `pagos.prestamo_id` NULL con cédula que tiene varios préstamos activos | No hay un solo crédito; el pago queda “sin asignar” hasta asignación manual o conciliación. |
| Préstamo de otro cliente | `pagos.prestamo_id` apunta a un préstamo cuyo `prestamos.cliente_id` no corresponde al cliente de `pagos.cedula_cliente` | Validación en endpoint (pago vs cedula del préstamo). No siempre aplicada en todos los flujos (ej. carga masiva con columna Crédito errónea). |
| Cuotas de otro préstamo | Por bug, `cuota_pagos` o `cuotas.pago_id` vinculan el pago a cuotas de otro préstamo | La lógica de aplicación a cuotas usa solo `pago.prestamo_id` y filtra por `Cuota.prestamo_id`; el test de relacionamiento único lo verifica. |
| Inconsistencia denormalizada | `prestamos.cedula` ≠ `clientes.cedula` para ese `cliente_id` | Mantenimiento/trigger o reglas de negocio al crear/actualizar préstamo. |

Para una **trazabilidad fiable** hace falta poder **consultar y validar** esta cadena cada vez que se quiera “verificar” a partir de un pago (o de una cédula).

---

## 4. Propuesta: trazabilidad verificable

### 4.1 Endpoint de trazabilidad por pago (recomendado)

Un endpoint que, dado un **pago_id** (o **numero_documento**), devuelva:

- **Cliente**: id, cedula, nombres (del cliente tal que `clientes.cedula = pagos.cedula_cliente`).
- **Préstamo**: id, estado, total_financiamiento, etc. (tal que `prestamos.id = pagos.prestamo_id`), solo si `pagos.prestamo_id` no es NULL.
- **Cuotas del préstamo**: listado de cuotas con `prestamo_id = pago.prestamo_id` (y opcionalmente cuáles tienen `total_pagado` / estado).
- **Detalle aplicación del pago**: filas de `cuota_pagos` para ese `pago_id` (cuota_id, monto_aplicado, orden_aplicacion).

Y que además devuelva un **resultado de verificación**:

- `cadena_ok`: true/false.
- `motivo`: si es false, por qué (ej. “cliente no encontrado”, “prestamo_id no coincide con cliente de la cédula”, “cuota_pagos con cuota de otro préstamo”, etc.).

Eso permite, al cargar un pago con referencia cédula, **comprobar que existe una sola línea de conexión cliente → préstamo → cuota → pago y que es solvente**.

### 4.2 Consulta por cédula

Variante o complemento: dado **cedula**, listar:

- El cliente con esa cédula.
- Los préstamos activos de ese cliente.
- Los pagos con `pagos.cedula_cliente = cedula` y su `prestamo_id`.
- Para cada pago con prestamo_id, el detalle de aplicación en cuotas (cuota_pagos).

Así se ve toda la “línea” por cédula y se puede revisar si cada pago está bien encadenado.

### 4.3 Reglas de validación concretas (para “única y solvente”)

1. **Cliente**: existe exactamente un cliente con `cedula = pagos.cedula_cliente`.
2. **Préstamo (si hay prestamo_id)**:
   - Existe `prestamos.id = pagos.prestamo_id`.
   - `prestamos.cliente_id` = `clientes.id` del cliente de la cédula.
   - Opcional: `prestamos.cedula` = `pagos.cedula_cliente`.
3. **Cuotas y cuota_pagos**:
   - Todas las filas de `cuota_pagos` con `pago_id = pago.id` tienen `cuota_id` en cuotas con `prestamo_id = pagos.prestamo_id`.
   - Suma de `monto_aplicado` para ese pago ≤ `pagos.monto_pagado`.

Si se implementa un endpoint de trazabilidad, estas reglas pueden ser el núcleo del campo `cadena_ok` y `motivo`.

---

## 5. Resumen

- La **referencia cédula** al cargar un pago es **pagos.cedula_cliente** (columna `cedula` en BD).
- La **única línea de conexión** deseada es: **Cliente** (por cédula) → **Préstamo** (por prestamo_id) → **Cuota** (por prestamo_id) → **Pago** (por id) y **CuotaPago** (detalle de aplicación).
- Para que sea **solvente**: la cédula del pago debe coincidir con el cliente del préstamo, y las cuotas/cuota_pagos deben ser solo del mismo préstamo y del mismo pago.
- Hoy la consistencia se asegura con FKs, validaciones en endpoints y la lógica FIFO de aplicación a cuotas; **no existe aún un punto único que “devuelva y valide” toda la cadena**.
- La **trazabilidad verificable** se consigue con un **endpoint de trazabilidad** (por pago_id o numero_documento, y opcionalmente por cedula) que devuelva la cadena y un indicador de si es única y solvente según las reglas anteriores.

Si quieres, el siguiente paso puede ser bajar esto a un **especificación de endpoint** (verb, path, request/response) y a **consultas SQL o servicios** concretos en el backend para implementarlo.
