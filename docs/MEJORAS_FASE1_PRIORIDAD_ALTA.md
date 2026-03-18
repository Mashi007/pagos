# Mejoras Fase 1 – Prioridad alta (cambios a aplicar)

Estos son los cambios concretos para implementar las 3 mejoras de prioridad alta en `backend/app/api/v1/endpoints/pagos.py`. Aplícalos manualmente si el IDE no permite editar el archivo.

---

## 1. Idempotencia en `_aplicar_pago_a_cuotas_interno`

**Ubicación:** función `_aplicar_pago_a_cuotas_interno` (aprox. línea 2061).

**Después de:**
```python
    if monto_restante <= 0:
        return 0, 0
    fecha_pago_date = pago.fecha_pago.date()...
```

**Insertar antes de `fecha_pago_date`:**
```python
    # Idempotencia: si ya existe aplicacion completa en cuota_pagos, no re-aplicar
    suma_aplicada = db.execute(
        select(func.coalesce(func.sum(CuotaPago.monto_aplicado), 0)).where(CuotaPago.pago_id == pago.id)
    ).scalar() or 0
    if float(suma_aplicada) >= monto_restante - 0.01:
        return 0, 0
```

**Además:** en el docstring de la función, añadir una línea:
```python
    Idempotente: si el pago ya fue aplicado (suma en cuota_pagos >= monto), no vuelve a aplicar.
```

---

## 2. Anti-duplicados y validación en batch (`crear_pagos_batch`)

**2.1 Validación de monto por ítem**

En la Fase 1 de validación (bucle `for idx, payload in enumerate(pagos_list):`), **después** de las comprobaciones de cedula/prestamo y **antes** de `if num_doc: docs_added_in_batch.add(num_doc)`, añadir:

```python
            es_valido, monto_val, err_msg = _validar_monto(payload.monto_pagado)
            if not es_valido:
                validation_errors.append({"index": idx, "error": err_msg, "status_code": 400})
                continue
```

**2.2 Prestamo pertenece al cliente**

Antes del bucle de validación (junto a los otros “Preload”), añadir la carga de prestamo_id -> cedula del cliente:

```python
        # Preload: prestamo_id -> cedula del titular (para validar que credito es del cliente)
        prestamo_cedula_map: dict[int, str] = {}
        if prestamo_ids:
            prestamo_cedula_rows = db.execute(
                select(Prestamo.id, Cliente.cedula).join(Cliente, Prestamo.cliente_id == Cliente.id).where(Prestamo.id.in_(prestamo_ids))
            ).all()
            prestamo_cedula_map = {r[0]: (r[1] or "").strip().upper() for r in prestamo_cedula_rows}
```

Dentro del mismo bucle de validación, **después** de validar `cedula_normalizada not in valid_cedulas` y **antes** de `if num_doc: docs_added_in_batch.add(num_doc)`:

```python
            if cedula_normalizada and payload.prestamo_id:
                cedula_titular = prestamo_cedula_map.get(payload.prestamo_id)
                if cedula_titular and cedula_titular != cedula_normalizada:
                    validation_errors.append({"index": idx, "error": f"El credito #{payload.prestamo_id} no pertenece al cliente con cedula {cedula_normalizada}.", "status_code": 400})
                    continue
```

---

## 3. Importar desde Cobros: marcar reportados importados

**3.1 Lista de reportados importados**

Donde se declara `pagos_creados: list[Pago] = []` (aprox. línea 913), añadir:

```python
    reportados_importados: list[PagoReportado] = []
```

**3.2 Al crear cada pago desde reportado**

Donde se hace `pagos_creados.append(p)` (aprox. línea 1093), justo después añadir:

```python
        reportados_importados.append(pr)
```

**3.3 Antes del commit**

Justo **antes** de `db.commit()` del importar (aprox. línea 1104), añadir:

```python
    for pr in reportados_importados:
        pr.estado = "importado"
```

Así los reportados ya convertidos a pago no se volverán a seleccionar en futuras importaciones (el `select` filtra por `estado == "aprobado"`).

---

## 4. Guardar fila editable: validación monto y prestamo–cliente

**4.1 Usar _validar_monto**

Sustituir la validación actual de monto (las líneas que hacen `if monto <= 0` e `if monto > _MAX_MONTO_PAGADO`) por:

```python
        es_valido, monto_val, err_msg = _validar_monto(monto)
        if not es_valido:
            raise HTTPException(status_code=400, detail=err_msg)
        monto = monto_val
```

Y usar `monto` (ya validado) en la creación del `Pago`.

**4.2 Prestamo pertenece al cliente**

Después de resolver `prestamo_id` (incluido el caso “Si prestamo_id es None, buscar automáticamente”) y **antes** de “Crear pago”, añadir:

```python
        if prestamo_id is not None:
            prestamo_row = db.execute(
                select(Prestamo.cliente_id).where(Prestamo.id == prestamo_id)
            ).first()
            if prestamo_row:
                cliente_row = db.execute(
                    select(Cliente.cedula).where(Cliente.id == prestamo_row[0])
                ).first()
                if cliente_row and (cliente_row[0] or "").strip().upper() != cedula.strip().upper():
                    raise HTTPException(
                        status_code=400,
                        detail=f"El credito #{prestamo_id} no pertenece al cliente con cedula {cedula}."
                    )
```

---

## Resumen

| Mejora | Archivo | Qué hace |
|-------|---------|----------|
| Idempotencia aplicar a cuotas | pagos.py | Al inicio de `_aplicar_pago_a_cuotas_interno`, si `SUM(cuota_pagos.monto_aplicado)` >= monto del pago, retorna (0,0) sin aplicar. |
| Validación monto en batch | pagos.py | En Fase 1 del batch, valida cada `monto_pagado` con `_validar_monto` y rechaza ítem con 400. |
| Prestamo–cliente en batch | pagos.py | Preload `prestamo_id -> cedula` y en validación rechaza si el credito no es del cliente. |
| Importar Cobros: no re-importar | pagos.py | Tras crear cada pago desde reportado, se agrega `pr` a `reportados_importados`; antes del commit se hace `pr.estado = "importado"`. |
| Guardar fila: monto y prestamo–cliente | pagos.py | Usa `_validar_monto` y valida que el credito pertenezca al cliente por cedula. |

Tras aplicar los cambios, ejecutar las pruebas (batch, importar-desde-cobros, guardar-fila-editable, aplicar-cuotas dos veces sobre el mismo pago) y revisar que no haya regresiones.
