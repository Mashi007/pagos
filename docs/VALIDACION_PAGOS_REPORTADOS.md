# Reglas de validación: Pagos reportados (Cobros)

Contexto: [Pagos reportados](https://rapicredit.onrender.com/pagos/cobros/pagos-reportados) — listado, filtros, cambio de estado, aprobar, rechazar, editar y eliminar.

## 0. Al cargar información (listado)

Al listar pagos reportados, se calculan observaciones por reglas y se muestran en la columna **Observación** (junto con las de Gemini si existen):

- **Cédula:** se consulta la tabla `clientes` (cédula normalizada). Si **no existe** el cliente → observación = **NO CLIENTES** (nota inicial; con aprobación manual sí se puede guardar, pero se muestra esta nota).
- **Monto:** si la moneda es **BS**, solo está permitido si la cédula está en la lista de Bolívares (`cedulas_reportar_bs`). Si no está en la lista → observación = **Monto: solo Bs si está en lista Bolívares**.
- **Nº de operación:** se consulta la tabla `pagos` (campo `numero_documento`). Si ya existe un pago con ese número → observación = **DUPLICADO DOC**. **Nunca se permite guardar** un número de operación duplicado (ni al editar ni al aprobar).

Varias observaciones se concatenan con " / " (p. ej. "NO CLIENTES / DUPLICADO DOC").

## 1. Estados válidos

- **Valores permitidos:** `pendiente`, `en_revision`, `aprobado`, `rechazado`.
- Cualquier otro valor en cambio de estado → **400** "Estado no válido".

## 2. Aprobar pago reportado

- **No aprobar si está rechazado** → 400 "No se puede aprobar un pago rechazado."
- **Nº de operación duplicado:** si ya existe un pago con ese número en `pagos.numero_documento` → 400 "Número de operación duplicado. No se permite guardar. Ya existe un pago con ese documento."
- **Cédula del reporte vacía** → 400 "Cédula del reporte vacía; no se puede crear el pago en préstamos."
- **Cliente no encontrado por cédula** → 400 "No se encontró cliente con la cédula indicada. Verifique la cédula o registre al cliente..."
- **Cliente sin préstamo APROBADO activo** → 400 "El cliente no tiene un préstamo APROBADO activo..."
- **Monto ≤ 0** → 400 "El monto del reporte debe ser mayor que cero."
- Si falla generación de recibo o creación de pago/cuotas → 500 con mensaje de error (ver logs).

## 3. Rechazar pago reportado

- **Motivo obligatorio:** no vacío ni solo espacios → 400 "El motivo de rechazo es obligatorio." / "El motivo es obligatorio al rechazar."
- Motivo truncado a **2000** caracteres al guardar.
- Frontend: validar antes de enviar que `motivoRechazo.trim()` no esté vacío; toast "El motivo de rechazo es obligatorio." si está vacío.

## 4. Cambiar estado (PATCH /pagos-reportados/{id}/estado)

- **Estado** debe ser uno de: `pendiente`, `en_revision`, `aprobado`, `rechazado`.
- Si **estado = rechazado** → **motivo** obligatorio (mismo criterio que rechazar).
- Si **estado = aprobado** y el pago actual está **rechazado** → 400 "No se puede aprobar un pago rechazado."
- Recurso no encontrado → 404 "Pago reportado no encontrado."

## 5. Editar pago reportado (PATCH /pagos-reportados/{id})

- **No editar si estado = aprobado** → 400 "No se puede editar un pago ya aprobado."
- **No editar si estado = rechazado** → 400 "No se puede editar un pago rechazado."
- **Nº de operación duplicado:** si el número de operación ya existe en tabla `pagos.numero_documento` → 400 "Número de operación duplicado. No se permite guardar. Ya existe un pago con ese documento." (nunca se permite guardar duplicado).
- **Cédula:** si se envían tipo/numero, se valida con `validate_cedula`; si no es válida → 400 "Cédula inválida." (o mensaje del validador). NO CLIENTES solo se muestra en observación; con aprobación manual sí se puede guardar.
- **Monto:** no negativo → 400 "El monto no puede ser negativo."
- **Moneda BS:** si la moneda final es BS, la cédula debe estar en la tabla `cedulas_reportar_bs`; si no → 400 "Observación: Bolívares. No puede guardar con moneda Bs; la cédula no está en la lista autorizada. Cambie a USD."
- Longitudes máximas al guardar: nombres/apellidos 200, institución/numero_operacion 100, numero_cedula 13, moneda 10, correo_enviado_a 255, observacion 500.
- **USDT** se normaliza a **USD** en backend.

## 6. Enviar recibo por correo (POST /pagos-reportados/{id}/enviar-recibo)

- Debe existir **correo del cliente** (por cédula o en el reporte); si no → 400 "No hay correo del cliente para este pago. Registre el correo en el detalle del pago o en la ficha del cliente."
- Pago no encontrado → 404.

## 7. Eliminar pago reportado

- Frontend: **confirmación** obligatoria (`window.confirm`) antes de llamar al DELETE.
- Backend: 404 si no existe.

## 8. Listado y filtros (GET /pagos-reportados y /pagos-reportados/kpis)

- **estado** opcional; si no se envía, el listado **excluye aprobados** por defecto (solo pendiente, en_revision, rechazado).
- **fecha_desde**, **fecha_hasta** (date), **cedula**, **institucion** opcionales; mismos criterios para listado y KPIs.
- **page** ≥ 1, **per_page** entre 1 y 100.

## 9. Comprobante y recibo PDF

- GET comprobante/recibo: 404 si no hay archivo almacenado ("No hay comprobante almacenado." / "No hay recibo PDF generado para este pago.").

## Resumen frontend (página CobrosPagosReportadosPage)

- Al **rechazar:** validar que el motivo no esté vacío antes de enviar; mostrar toast si está vacío.
- Al **eliminar:** pedir confirmación.
- Al **cambiar estado** desde el desplegable a "Rechazar": abrir modal y exigir motivo; no enviar sin motivo.
- Mensajes de error: mostrar `e?.message` o `detail` del API en toast.
- KPIs y listado usan los mismos filtros (fecha, cédula, institución); al hacer clic en un KPI se filtra por ese estado.
